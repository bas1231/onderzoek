from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA = "PVA_ASTRA_REVIEW_V1"
MODEL_PROVENANCE_SCHEMA = "PVA_MODEL_ROUTE_ATTESTATION_V1"
AUTONOMOUS_PROVENANCE_SCHEMA = "PVA_ASTRA_RUN_PROVENANCE_V1"
MODEL_PROVENANCE_TEST_METHOD = "HUMAN_SELECTED_CHATGPT_MODEL_UI"
MODEL_PROVENANCE_PRODUCTION_METHOD = "AUTONOMOUS_WORKER_MODEL_SLUG"
MODEL_PROVENANCE_TEST_SCOPE = "TEST_ONLY"
MODEL_PROVENANCE_PRODUCTION_SCOPE = "PRODUCTION_AUTONOMOUS"
PROVENANCE_TEST_ROUTE = "TEST_ROUTE"
PROVENANCE_AUTONOMOUS_RUN = "AUTONOMOUS_RUN"
REQUIRED_REVIEWER_MODEL = "GPT-6 Astra"
ECONOMIC_POLICY = "ANY_POSITIVE_NET_EDGE_COUNTS"
PHASES = {"PREBUILD", "PREMEASUREMENT"}
DECISIONS = {"APPROVE", "REJECT", "REVISE"}


class ReviewGateError(ValueError):
    pass


def canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def economic_signal_counts(net_profit_eur: float) -> bool:
    try:
        value = float(net_profit_eur)
    except (TypeError, ValueError) as exc:
        raise ReviewGateError("NET_PROFIT_INVALID") from exc
    return value > 0.0


def review_binding(overlay: dict[str, Any], phase: str) -> str:
    if phase not in PHASES:
        raise ReviewGateError("REVIEW_PHASE_INVALID")
    if not isinstance(overlay, dict) or not overlay.get("candidate_id"):
        raise ReviewGateError("OVERLAY_INVALID")
    payload = {
        "phase": phase,
        "candidate_id": overlay.get("candidate_id"),
        "source_hashes": overlay.get("source_hashes"),
        "originating_task_id": overlay.get("originating_task_id"),
        "completion_hash": overlay.get("completion_hash"),
        "validation_hash": overlay.get("validation_hash"),
        "finding": overlay.get("finding"),
        "next_action": overlay.get("next_action"),
        "candidate_snapshot": overlay.get("candidate_snapshot"),
        "referenced_evidence_hash": canonical_sha(overlay.get("referenced_evidence", {})),
    }
    return canonical_sha(payload)


def expected_review_ref(overlay: dict[str, Any], phase: str) -> str:
    cid = str(overlay["candidate_id"])
    binding = review_binding(overlay, phase)
    return f"knowledge/reviews/astra/{cid}-{phase.lower()}-{binding[:20]}.json"


def is_qualification_fixture(overlay: dict[str, Any]) -> bool:
    snapshot = overlay.get("candidate_snapshot") if isinstance(overlay, dict) else None
    if isinstance(snapshot, dict) and snapshot.get("qualification_fixture") is True:
        return True
    return bool(isinstance(overlay, dict) and overlay.get("qualification_fixture") is True)


def expected_model_provenance_ref(route_task_id: str) -> str:
    route = str(route_task_id or "").strip()
    if (
        not route.startswith("SESSION-ROUTE-")
        or len(route) > 160
        or any(ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._:-" for ch in route)
    ):
        raise ReviewGateError("ASTRA_MODEL_PROVENANCE_ROUTE_INVALID")
    return f"control/model_provenance/astra_routes/{route}.json"


def expected_autonomous_provenance_ref(overlay: dict[str, Any], phase: str) -> str:
    cid = str(overlay.get("candidate_id") or "")
    if not cid:
        raise ReviewGateError("ASTRA_AUTONOMOUS_PROVENANCE_CANDIDATE")
    binding = review_binding(overlay, phase)
    return f"knowledge/reviews/astra/provenance/{cid}-{phase.lower()}-{binding[:20]}.json"


def load_model_provenance(
    repo: Path,
    route_task_id: str,
    *,
    allow_test_only: bool = False,
) -> tuple[dict[str, Any], str, str]:
    ref = expected_model_provenance_ref(route_task_id)
    path = Path(repo) / ref
    if not path.exists():
        raise ReviewGateError("ASTRA_MODEL_PROVENANCE_MISSING")
    if path.is_symlink():
        raise ReviewGateError("ASTRA_MODEL_PROVENANCE_SYMLINK")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ReviewGateError("ASTRA_MODEL_PROVENANCE_INVALID_JSON") from exc
    if not isinstance(value, dict) or value.get("schema") != MODEL_PROVENANCE_SCHEMA:
        raise ReviewGateError("ASTRA_MODEL_PROVENANCE_SCHEMA")
    if value.get("route_task_id") != route_task_id:
        raise ReviewGateError("ASTRA_MODEL_PROVENANCE_ROUTE_MISMATCH")
    if value.get("reviewer_model") != REQUIRED_REVIEWER_MODEL:
        raise ReviewGateError("ASTRA_MODEL_PROVENANCE_WRONG_MODEL")
    if value.get("reviewer_role") != "INDEPENDENT_GATE_REVIEWER":
        raise ReviewGateError("ASTRA_MODEL_PROVENANCE_ROLE")
    if value.get("attestation_scope") != "ROUTE":
        raise ReviewGateError("ASTRA_MODEL_PROVENANCE_SCOPE")
    usage_scope = value.get("usage_scope")
    method = value.get("verification_method")
    if usage_scope == MODEL_PROVENANCE_TEST_SCOPE:
        if method != MODEL_PROVENANCE_TEST_METHOD:
            raise ReviewGateError("ASTRA_MODEL_PROVENANCE_METHOD")
        if not allow_test_only:
            raise ReviewGateError("ASTRA_TEST_ONLY_PROVENANCE_FORBIDDEN_IN_PRODUCTION")
    elif usage_scope == MODEL_PROVENANCE_PRODUCTION_SCOPE:
        raise ReviewGateError("ASTRA_ROUTE_PROVENANCE_FORBIDDEN_IN_PRODUCTION")
    else:
        raise ReviewGateError("ASTRA_MODEL_PROVENANCE_USAGE_SCOPE")
    if value.get("revoked") is not False:
        raise ReviewGateError("ASTRA_MODEL_PROVENANCE_REVOKED")
    return value, ref, canonical_sha(value)


def load_autonomous_provenance(
    repo: Path,
    overlay: dict[str, Any],
    phase: str,
    review: dict[str, Any],
) -> tuple[dict[str, Any], str, str]:
    ref = expected_autonomous_provenance_ref(overlay, phase)
    path = Path(repo) / ref
    if not path.exists():
        raise ReviewGateError("ASTRA_AUTONOMOUS_PROVENANCE_MISSING")
    if path.is_symlink():
        raise ReviewGateError("ASTRA_AUTONOMOUS_PROVENANCE_SYMLINK")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ReviewGateError("ASTRA_AUTONOMOUS_PROVENANCE_INVALID_JSON") from exc
    if not isinstance(value, dict) or value.get("schema") != AUTONOMOUS_PROVENANCE_SCHEMA:
        raise ReviewGateError("ASTRA_AUTONOMOUS_PROVENANCE_SCHEMA")
    binding = review_binding(overlay, phase)
    expected = {
        "usage_scope": MODEL_PROVENANCE_PRODUCTION_SCOPE,
        "verification_method": MODEL_PROVENANCE_PRODUCTION_METHOD,
        "reviewer_model": REQUIRED_REVIEWER_MODEL,
        "reviewer_role": "INDEPENDENT_GATE_REVIEWER",
        "candidate_id": overlay.get("candidate_id"),
        "phase": phase,
        "binding_sha256": binding,
        "model_policy": "ASTRA_EXACT",
        "visible_astra_count": 1,
    }
    for key, wanted in expected.items():
        if value.get(key) != wanted:
            raise ReviewGateError("ASTRA_AUTONOMOUS_PROVENANCE_" + key.upper())
    slug = value.get("reviewer_model_slug")
    if not isinstance(slug, str) or not slug.strip():
        raise ReviewGateError("ASTRA_AUTONOMOUS_PROVENANCE_MODEL_SLUG")
    if review.get("reviewer_model_slug") != slug:
        raise ReviewGateError("ASTRA_REVIEW_MODEL_SLUG_MISMATCH")
    if review.get("model_provenance_ref") != ref:
        raise ReviewGateError("ASTRA_REVIEW_PROVENANCE_REF")
    digest = canonical_sha(value)
    if review.get("model_provenance_sha256") != digest:
        raise ReviewGateError("ASTRA_REVIEW_PROVENANCE_HASH")
    if review.get("source_task_id") != value.get("source_task_id"):
        raise ReviewGateError("ASTRA_REVIEW_SOURCE_TASK")
    if review.get("completion_sha256") != value.get("completion_sha256"):
        raise ReviewGateError("ASTRA_REVIEW_COMPLETION_HASH")
    return value, ref, digest


def validate_review(
    review: dict[str, Any],
    overlay: dict[str, Any],
    phase: str,
    *,
    repo: Path | None = None,
) -> dict[str, Any]:
    if not isinstance(review, dict) or review.get("schema") != SCHEMA:
        raise ReviewGateError("ASTRA_REVIEW_SCHEMA")
    if phase not in PHASES or review.get("phase") != phase:
        raise ReviewGateError("ASTRA_REVIEW_PHASE")
    if review.get("candidate_id") != overlay.get("candidate_id"):
        raise ReviewGateError("ASTRA_REVIEW_CANDIDATE")
    if review.get("reviewer_model") != REQUIRED_REVIEWER_MODEL:
        raise ReviewGateError("ASTRA_REVIEW_WRONG_MODEL")
    if review.get("reviewer_role") != "INDEPENDENT_GATE_REVIEWER":
        raise ReviewGateError("ASTRA_REVIEW_ROLE")
    if review.get("decision") not in DECISIONS:
        raise ReviewGateError("ASTRA_REVIEW_DECISION")
    if review.get("binding_sha256") != review_binding(overlay, phase):
        raise ReviewGateError("ASTRA_REVIEW_STALE_BINDING")
    if review.get("economic_policy") != ECONOMIC_POLICY:
        raise ReviewGateError("ASTRA_REVIEW_ECONOMIC_POLICY")
    if float(review.get("minimum_net_profit_eur", -1)) != 0.0:
        raise ReviewGateError("ASTRA_REVIEW_MINIMUM_PROFIT_CHANGED")
    if review.get("measurement_scope") != "READ_ONLY_PROSPECTIVE_MARKET_DATA":
        raise ReviewGateError("ASTRA_REVIEW_MEASUREMENT_SCOPE")
    if review.get("live_trading") is not False:
        raise ReviewGateError("ASTRA_REVIEW_LIVE_TRADING")
    if review.get("paid_actions") is not False:
        raise ReviewGateError("ASTRA_REVIEW_PAID_ACTIONS")
    if review.get("wallet_actions") is not False:
        raise ReviewGateError("ASTRA_REVIEW_WALLET_ACTIONS")
    if repo is None:
        raise ReviewGateError("ASTRA_REVIEW_PROVENANCE_CONTEXT_REQUIRED")

    kind = review.get("provenance_kind")
    if kind == PROVENANCE_TEST_ROUTE:
        if not is_qualification_fixture(overlay):
            raise ReviewGateError("ASTRA_TEST_ROUTE_FORBIDDEN_IN_PRODUCTION")
        route_task_id = str(review.get("reviewer_route_task_id") or "").strip()
        if not route_task_id:
            raise ReviewGateError("ASTRA_REVIEW_ROUTE_MISSING")
        _, expected_ref, expected_sha = load_model_provenance(
            Path(repo),
            route_task_id,
            allow_test_only=True,
        )
        if review.get("model_provenance_ref") != expected_ref:
            raise ReviewGateError("ASTRA_REVIEW_PROVENANCE_REF")
        if review.get("model_provenance_sha256") != expected_sha:
            raise ReviewGateError("ASTRA_REVIEW_PROVENANCE_HASH")
    elif kind == PROVENANCE_AUTONOMOUS_RUN:
        load_autonomous_provenance(Path(repo), overlay, phase, review)
    else:
        raise ReviewGateError("ASTRA_REVIEW_PROVENANCE_KIND")

    finding = review.get("finding")
    next_action = review.get("next_action")
    if not isinstance(finding, str) or not finding.strip():
        raise ReviewGateError("ASTRA_REVIEW_FINDING")
    if not isinstance(next_action, str) or not next_action.strip():
        raise ReviewGateError("ASTRA_REVIEW_NEXT_ACTION")
    return review


def load_review(repo: Path, overlay: dict[str, Any], phase: str) -> tuple[dict[str, Any] | None, str]:
    ref = expected_review_ref(overlay, phase)
    path = Path(repo) / ref
    if not path.exists():
        return None, ref
    if path.is_symlink():
        raise ReviewGateError("ASTRA_REVIEW_SYMLINK")
    try:
        review = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ReviewGateError("ASTRA_REVIEW_INVALID_JSON") from exc
    return validate_review(review, overlay, phase, repo=Path(repo)), ref


def review_template(
    overlay: dict[str, Any],
    phase: str,
    *,
    route_task_id: str,
    model_provenance_ref: str,
    model_provenance_sha256: str,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "candidate_id": overlay["candidate_id"],
        "phase": phase,
        "binding_sha256": review_binding(overlay, phase),
        "reviewer_model": REQUIRED_REVIEWER_MODEL,
        "reviewer_role": "INDEPENDENT_GATE_REVIEWER",
        "provenance_kind": PROVENANCE_TEST_ROUTE,
        "reviewer_route_task_id": route_task_id,
        "model_provenance_ref": model_provenance_ref,
        "model_provenance_sha256": model_provenance_sha256,
        "decision": "APPROVE|REJECT|REVISE",
        "finding": "required",
        "next_action": "required",
        "economic_policy": ECONOMIC_POLICY,
        "minimum_net_profit_eur": 0.0,
        "measurement_scope": "READ_ONLY_PROSPECTIVE_MARKET_DATA",
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
    }


def apply_review(supervisor, repo: Path, overlay_path: Path, phase: str):
    from supervisor import atomic

    overlay_path = Path(overlay_path)
    overlay = json.loads(overlay_path.read_text(encoding="utf-8"))
    review, ref = load_review(Path(repo), overlay, phase)
    if review is None:
        return None, ref

    decision = review["decision"]
    meta = {
        "ref": ref,
        "binding_sha256": review["binding_sha256"],
        "reviewer_model": review["reviewer_model"],
        "provenance_kind": review["provenance_kind"],
        "model_provenance_ref": review["model_provenance_ref"],
        "model_provenance_sha256": review["model_provenance_sha256"],
        "decision": decision,
        "finding": review["finding"],
        "next_action": review["next_action"],
    }
    for key in (
        "reviewer_route_task_id",
        "reviewer_model_slug",
        "source_task_id",
        "completion_sha256",
    ):
        if key in review:
            meta[key] = review[key]

    next_state = dict(overlay)
    next_state.setdefault("astra_reviews", {})[phase] = meta

    if decision == "REJECT":
        next_state["queue_status"] = "REJECT"
    elif decision == "REVISE":
        next_state["queue_status"] = "NEEDS_REVISION"
    elif phase == "PREBUILD":
        next_state["queue_status"] = "NEEDS_BUILD"
        pending = next_state.pop("pending_build_handoff", None)
        if pending:
            pending = dict(pending)
            pending["status"] = "BUILD_TASK_QUEUED"
            pending["astra_prebuild_review_ref"] = ref
            next_state["build_handoff"] = pending
    else:
        next_state["queue_status"] = "MEASUREMENT_READY"
        next_state["measurement_authorization"] = {
            "authorized": True,
            "scope": "READ_ONLY_PROSPECTIVE_MARKET_DATA",
            "astra_premeasurement_review_ref": ref,
            "order_submission": False,
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
        }

    atomic(overlay_path, next_state)
    return next_state, ref
