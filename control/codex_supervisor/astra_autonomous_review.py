from __future__ import annotations

import hashlib
import json
from pathlib import Path

P = Path
DECISIONS = {"APPROVE", "REJECT", "REVISE"}


class AstraAutonomousReviewError(ValueError):
    pass


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _immutable_write(path: P, value: dict) -> None:
    from supervisor import atomic
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if path.exists():
        if path.is_symlink():
            raise AstraAutonomousReviewError("ASTRA_REVIEW_OUTPUT_SYMLINK")
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise AstraAutonomousReviewError("ASTRA_REVIEW_OUTPUT_INVALID") from exc
        if existing != value:
            raise AstraAutonomousReviewError("ASTRA_REVIEW_OUTPUT_CONFLICT")
        return
    atomic(path, payload)


def select_task(supervisor, repo: P, overlay_path: P, overlay: dict, phase: str) -> dict | None:
    import model_quality_gate as q

    if phase not in q.PHASES:
        raise AstraAutonomousReviewError("ASTRA_REVIEW_PHASE_INVALID")
    required_state = "ASTRA_PREBUILD_REVIEW" if phase == "PREBUILD" else "ASTRA_PREMEASUREMENT_REVIEW"
    if overlay.get("queue_status") != required_state:
        raise AstraAutonomousReviewError("ASTRA_REVIEW_STATE_INVALID")
    if q.is_qualification_fixture(overlay):
        raise AstraAutonomousReviewError("ASTRA_AUTONOMOUS_REVIEW_NOT_FOR_QUALIFICATION_FIXTURE")
    if any(overlay.get(flag) is not False for flag in ("live_trading", "paid_actions", "wallet_actions")):
        raise AstraAutonomousReviewError("ASTRA_REVIEW_UNSAFE_FLAGS")

    binding = q.review_binding(overlay, phase)
    cid = str(overlay.get("candidate_id") or "")
    source_task_id = "ASTRA-AUTO-REVIEW-" + hashlib.sha256(
        (cid + phase + binding).encode("utf-8")
    ).hexdigest()[:40]
    if supervisor.db.execute("select 1 from tasks where id=?", (source_task_id,)).fetchone():
        return None

    overlay_path = P(overlay_path)
    if overlay_path.is_symlink() or not overlay_path.is_file():
        raise AstraAutonomousReviewError("ASTRA_REVIEW_OVERLAY_INVALID")
    root = P(supervisor.root).resolve()
    if not overlay_path.resolve().is_relative_to((root / "candidate_states").resolve()):
        raise AstraAutonomousReviewError("ASTRA_REVIEW_OVERLAY_OUTSIDE_RUNTIME")

    review_ref = q.expected_review_ref(overlay, phase)
    provenance_ref = q.expected_autonomous_provenance_ref(overlay, phase)
    model_input = {
        "candidate_id": cid,
        "phase": phase,
        "binding_sha256": binding,
        "director_finding": overlay.get("finding"),
        "director_next_action": overlay.get("next_action"),
        "candidate_snapshot": overlay.get("candidate_snapshot"),
        "referenced_evidence": overlay.get("referenced_evidence"),
        "scientific_status": overlay.get("scientific_status"),
        "economic_policy": q.ECONOMIC_POLICY,
        "minimum_net_profit_eur": 0.0,
        "measurement_scope": "READ_ONLY_PROSPECTIVE_MARKET_DATA",
        "safety": {
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
        },
    }
    prompt = (
        "Act as the independent GPT-6 Astra gate reviewer. Reason only over the supplied immutable input. "
        "Do not call tools, execute commands, change files, spend money, trade, use wallets or assume missing evidence. "
        "Any strictly positive NET executable euro edge is worth testing, but evidence quality, fees, slippage, fill probability, "
        "limits, reproducibility and falsification remain mandatory. "
        "For PREBUILD decide whether the bounded proposed falsification/build is worth implementing. "
        "For PREMEASUREMENT decide whether the exact tested version is safe and scientifically adequate for read-only prospective market observation. "
        "Return ONLY JSON with exactly: candidate_id, phase, binding_sha256, decision, finding, next_action. "
        "decision must be APPROVE, REJECT or REVISE. Never claim PROVEN_EDGE.\n"
        + json.dumps(model_input, ensure_ascii=False, sort_keys=True)
    )
    if len(prompt) > 100000:
        raise AstraAutonomousReviewError("ASTRA_REVIEW_PROMPT_TOO_LARGE")

    return {
        "task_id": source_task_id,
        "task_class": "research_review",
        "priority": 100,
        "expected_value": 10,
        "estimated_reasoning_cost": 2,
        "created_at": overlay.get("decision_timestamp"),
        "prompt": prompt,
        "input_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "astra_review_task": True,
        "model_policy": "ASTRA_EXACT",
        "candidate_id": cid,
        "phase": phase,
        "binding_sha256": binding,
        "overlay_path": str(overlay_path),
        "overlay_sha256": _sha_bytes(overlay_path.read_bytes()),
        "candidate_source_root": str(P(repo)),
        "review_ref": review_ref,
        "provenance_ref": provenance_ref,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
    }


def validate_result_and_write(supervisor, task: dict, final: str, folder: P) -> dict:
    import model_quality_gate as q

    try:
        result = json.loads(final)
    except Exception as exc:
        raise AstraAutonomousReviewError("ASTRA_REVIEW_RESULT_JSON") from exc
    if not isinstance(result, dict):
        raise AstraAutonomousReviewError("ASTRA_REVIEW_RESULT_SHAPE")
    if result.get("candidate_id") != task.get("candidate_id"):
        raise AstraAutonomousReviewError("ASTRA_REVIEW_RESULT_CANDIDATE")
    if result.get("phase") != task.get("phase"):
        raise AstraAutonomousReviewError("ASTRA_REVIEW_RESULT_PHASE")
    if result.get("binding_sha256") != task.get("binding_sha256"):
        raise AstraAutonomousReviewError("ASTRA_REVIEW_RESULT_BINDING")
    if result.get("decision") not in DECISIONS:
        raise AstraAutonomousReviewError("ASTRA_REVIEW_RESULT_DECISION")
    for key in ("finding", "next_action"):
        if not isinstance(result.get(key), str) or not result[key].strip():
            raise AstraAutonomousReviewError("ASTRA_REVIEW_RESULT_" + key.upper())

    overlay_path = P(str(task.get("overlay_path") or ""))
    root = P(supervisor.root).resolve()
    if (
        not overlay_path.is_file()
        or overlay_path.is_symlink()
        or not overlay_path.resolve().is_relative_to((root / "candidate_states").resolve())
        or _sha_bytes(overlay_path.read_bytes()) != task.get("overlay_sha256")
    ):
        raise AstraAutonomousReviewError("ASTRA_REVIEW_OVERLAY_CHANGED")
    overlay = json.loads(overlay_path.read_text(encoding="utf-8"))
    if q.review_binding(overlay, task["phase"]) != task["binding_sha256"]:
        raise AstraAutonomousReviewError("ASTRA_REVIEW_BINDING_CHANGED")

    worker_path = P(folder) / "WORKER.json"
    if not worker_path.is_file() or worker_path.is_symlink():
        raise AstraAutonomousReviewError("ASTRA_WORKER_RECORD_MISSING")
    worker_raw = worker_path.read_bytes()
    worker = json.loads(worker_raw)
    selection = worker.get("model_selection")
    if not isinstance(selection, dict):
        raise AstraAutonomousReviewError("ASTRA_WORKER_SELECTION_MISSING")
    if selection.get("policy") != "ASTRA_EXACT":
        raise AstraAutonomousReviewError("ASTRA_WORKER_POLICY")
    if selection.get("visible_astra_count") != 1:
        raise AstraAutonomousReviewError("ASTRA_WORKER_AMBIGUOUS")
    slug = str(worker.get("model") or "")
    if not slug or selection.get("selected_slug") != slug:
        raise AstraAutonomousReviewError("ASTRA_WORKER_MODEL_MISMATCH")

    completion_sha = hashlib.sha256(final.encode("utf-8")).hexdigest()
    provenance = {
        "schema": q.AUTONOMOUS_PROVENANCE_SCHEMA,
        "usage_scope": q.MODEL_PROVENANCE_PRODUCTION_SCOPE,
        "verification_method": q.MODEL_PROVENANCE_PRODUCTION_METHOD,
        "reviewer_model": q.REQUIRED_REVIEWER_MODEL,
        "reviewer_role": "INDEPENDENT_GATE_REVIEWER",
        "reviewer_model_slug": slug,
        "model_policy": "ASTRA_EXACT",
        "visible_astra_count": 1,
        "candidate_id": task["candidate_id"],
        "phase": task["phase"],
        "binding_sha256": task["binding_sha256"],
        "source_task_id": task["task_id"],
        "input_sha256": task["input_sha256"],
        "completion_sha256": completion_sha,
        "worker_record_sha256": _sha_bytes(worker_raw),
        "model_selection": selection,
    }

    repo = P(task["candidate_source_root"])
    provenance_ref = q.expected_autonomous_provenance_ref(overlay, task["phase"])
    if provenance_ref != task.get("provenance_ref"):
        raise AstraAutonomousReviewError("ASTRA_PROVENANCE_REF_CHANGED")
    provenance_path = repo / provenance_ref
    provenance_path.parent.mkdir(parents=True, exist_ok=True)
    _immutable_write(provenance_path, provenance)
    provenance_sha = q.canonical_sha(provenance)

    review = {
        "schema": q.SCHEMA,
        "candidate_id": task["candidate_id"],
        "phase": task["phase"],
        "binding_sha256": task["binding_sha256"],
        "reviewer_model": q.REQUIRED_REVIEWER_MODEL,
        "reviewer_role": "INDEPENDENT_GATE_REVIEWER",
        "provenance_kind": q.PROVENANCE_AUTONOMOUS_RUN,
        "reviewer_model_slug": slug,
        "source_task_id": task["task_id"],
        "completion_sha256": completion_sha,
        "model_provenance_ref": provenance_ref,
        "model_provenance_sha256": provenance_sha,
        "decision": result["decision"],
        "finding": result["finding"],
        "next_action": result["next_action"],
        "economic_policy": q.ECONOMIC_POLICY,
        "minimum_net_profit_eur": 0.0,
        "measurement_scope": "READ_ONLY_PROSPECTIVE_MARKET_DATA",
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
    }
    q.validate_review(review, overlay, task["phase"], repo=repo)

    review_ref = q.expected_review_ref(overlay, task["phase"])
    if review_ref != task.get("review_ref"):
        raise AstraAutonomousReviewError("ASTRA_REVIEW_REF_CHANGED")
    review_path = repo / review_ref
    review_path.parent.mkdir(parents=True, exist_ok=True)
    _immutable_write(review_path, review)
    return {
        "candidate_id": task["candidate_id"],
        "phase": task["phase"],
        "decision": review["decision"],
        "finding": review["finding"],
        "next_action": review["next_action"],
        "reviewer_model": review["reviewer_model"],
        "reviewer_model_slug": slug,
        "source_task_id": task["task_id"],
        "input_sha256": task["input_sha256"],
        "completion_sha256": completion_sha,
        "binding_sha256": task["binding_sha256"],
        "review_ref": review_ref,
        "provenance_ref": provenance_ref,
        "model_provenance_sha256": provenance_sha,
    }
