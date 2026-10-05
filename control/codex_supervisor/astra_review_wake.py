from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

P = Path
SCHEMA = "PVA_ASTRA_REVIEW_WAKE_V1"
BRIDGE_DATA = P.home() / ".local" / "share" / "prediction-chat-bridge"
ROUTE_CONFIG = BRIDGE_DATA / "autobuild_control_route.json"
ROUTES = BRIDGE_DATA / "routes"


class AstraReviewWakeBlocked(RuntimeError):
    pass


def _load_json(path: P, reason: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise AstraReviewWakeBlocked(reason) from exc
    if not isinstance(value, dict):
        raise AstraReviewWakeBlocked(reason)
    return value


def _load_continuation():
    path = P(__file__).resolve().parents[1] / "tampermonkey_multichat" / "continuation_manager.py"
    spec = importlib.util.spec_from_file_location("prediction_astra_review_continuation", path)
    if spec is None or spec.loader is None:
        raise AstraReviewWakeBlocked("ASTRA_CONTINUATION_MODULE_UNAVAILABLE")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _control_route():
    config = _load_json(ROUTE_CONFIG, "ASTRA_ROUTE_CONFIG_INVALID")
    route_task_id = str(config.get("route_task_id") or "").strip()
    route = _load_json(ROUTES / f"{route_task_id}.json", "ASTRA_ROUTE_BINDING_INVALID")
    chat_id = str(route.get("chat_id") or "").strip()
    if not route_task_id or not chat_id:
        raise AstraReviewWakeBlocked("ASTRA_ROUTE_INVALID")
    return route_task_id, chat_id


def ensure_review_continuation(supervisor, repo: P, overlay: dict, phase: str) -> dict:
    import model_quality_gate

    if phase == "PREBUILD" and overlay.get("queue_status") != "ASTRA_PREBUILD_REVIEW":
        raise AstraReviewWakeBlocked("ASTRA_PREBUILD_STATE_REQUIRED")
    if phase == "PREMEASUREMENT" and overlay.get("queue_status") != "ASTRA_PREMEASUREMENT_REVIEW":
        raise AstraReviewWakeBlocked("ASTRA_PREMEASUREMENT_STATE_REQUIRED")

    review, ref = model_quality_gate.load_review(P(repo), overlay, phase)
    if review is not None:
        return {
            "candidate_id": overlay["candidate_id"],
            "phase": phase,
            "review_ref": ref,
            "continuation_state": "REVIEW_ALREADY_AVAILABLE",
        }

    route_task_id, chat_id = _control_route()
    try:
        _, provenance_ref, provenance_sha = model_quality_gate.load_model_provenance(
            P(repo),
            route_task_id,
            allow_test_only=model_quality_gate.is_qualification_fixture(overlay),
        )
    except model_quality_gate.ReviewGateError as exc:
        raise AstraReviewWakeBlocked(
            "ASTRA_MODEL_PROVENANCE_INVALID:" + str(exc)[:100]
        ) from exc

    binding = model_quality_gate.review_binding(overlay, phase)
    source_task_id = "ASTRA-REVIEW-" + hashlib.sha256(
        (overlay["candidate_id"] + phase + binding).encode("utf-8")
    ).hexdigest()[:40]
    template = model_quality_gate.review_template(
        overlay,
        phase,
        route_task_id=route_task_id,
        model_provenance_ref=provenance_ref,
        model_provenance_sha256=provenance_sha,
    )
    context = (
        "PREDICTION_ASTRA_REVIEW_REQUEST_V2\n"
        "required_model=GPT-6 Astra\n"
        f"phase={phase}\n"
        f"candidate_id={overlay['candidate_id']}\n"
        f"binding_sha256={binding}\n"
        f"review_ref={ref}\n"
        f"reviewer_route_task_id={route_task_id}\n"
        f"model_provenance_ref={provenance_ref}\n"
        f"model_provenance_sha256={provenance_sha}\n"
        "model_identity_verification=EXTERNAL_ROUTE_ATTESTATION_TEST_ONLY\n"
        "economic_policy=ANY_POSITIVE_NET_EDGE_COUNTS\n"
        "minimum_net_profit_eur=0.0\n"
        "measurement_scope=READ_ONLY_PROSPECTIVE_MARKET_DATA\n"
        "IMPORTANT: this browser-route review path is valid only for an explicitly marked qualification fixture. "
        "Do not self-attest your model identity. The deterministic gate will independently verify the immutable test-only route provenance, exact route and candidate binding. "
        "Production candidates must use autonomous model-run provenance and must not use this browser-route path. "
        "If the supplied route/provenance facts are missing or inconsistent with canonical Git, choose BLOCKED. "
        "Inspect the exact current canonical candidate/evidence and the supplied immutable overlay facts. "
        "Do not reject an idea merely because expected profit is small: any strictly positive NET executable euro edge is worth testing. "
        "Evidence quality, reproducibility, fees, slippage, fill probability, limits and capital/time cost still matter. "
        "For PREBUILD decide whether the proposed falsification/build is worth implementing. "
        "For PREMEASUREMENT decide whether tested code is safe and scientifically adequate to run prospectively on current public market data. "
        "Measurement means read-only/shadow observation only: no orders, no live trading, no wallets, no paid actions. "
        "If APPROVE/REJECT/REVISE, create exactly the canonical JSON review file at review_ref via the GitHub connector, using this exact template shape and exact binding/provenance fields; "
        "set finding and next_action substantively. Then choose DONE. Do not change candidate code or build code during review.\n"
        "review_template=" + json.dumps(template, sort_keys=True, ensure_ascii=False)
    )
    if len(context) > 6000:
        raise AstraReviewWakeBlocked("ASTRA_REVIEW_CONTEXT_TOO_LARGE")

    continuation = _load_continuation()
    record = continuation.start_external_continuation(
        data_dir=BRIDGE_DATA,
        source_task_id=source_task_id,
        chat_id=chat_id,
        expected_route_task_id=route_task_id,
        context_message=context,
        source_kind="ASTRA_" + phase + "_REVIEW",
    )
    audit = {
        "schema": SCHEMA,
        "candidate_id": overlay["candidate_id"],
        "phase": phase,
        "binding_sha256": binding,
        "required_model": "GPT-6 Astra",
        "review_ref": ref,
        "continuation_id": record["continuation_id"],
        "control_route_task_id": route_task_id,
        "model_provenance_ref": provenance_ref,
        "model_provenance_sha256": provenance_sha,
        "model_identity_verification": "EXTERNAL_ROUTE_ATTESTATION_TEST_ONLY",
        "economic_policy": "ANY_POSITIVE_NET_EDGE_COUNTS",
        "measurement_scope": "READ_ONLY_PROSPECTIVE_MARKET_DATA",
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
    }
    audit_path = P(supervisor.root) / "astra_review_wakes" / f"{source_task_id}.json"
    if audit_path.exists():
        if _load_json(audit_path, "ASTRA_WAKE_AUDIT_INVALID") != audit:
            raise AstraReviewWakeBlocked("ASTRA_WAKE_AUDIT_CONFLICT")
    else:
        from supervisor import atomic
        atomic(audit_path, audit)
    return {
        "candidate_id": overlay["candidate_id"],
        "phase": phase,
        "binding_sha256": binding,
        "review_ref": ref,
        "continuation_id": record["continuation_id"],
        "continuation_state": record["state"],
        "control_route_task_id": route_task_id,
        "model_provenance_ref": provenance_ref,
        "model_provenance_sha256": provenance_sha,
        "audit_ref": str(audit_path.relative_to(P(supervisor.root))),
    }
