from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

P = Path
SCHEMA = "PVA_MEASUREMENT_WAKE_V1"
BRIDGE_DATA = P.home() / ".local" / "share" / "prediction-chat-bridge"
ROUTE_CONFIG = BRIDGE_DATA / "autobuild_control_route.json"
ROUTES = BRIDGE_DATA / "routes"


class MeasurementWakeBlocked(RuntimeError):
    pass


def _load_json(path: P, reason: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise MeasurementWakeBlocked(reason) from exc
    if not isinstance(value, dict):
        raise MeasurementWakeBlocked(reason)
    return value


def _load_continuation():
    path = P(__file__).resolve().parents[1] / "tampermonkey_multichat" / "continuation_manager.py"
    spec = importlib.util.spec_from_file_location("prediction_measurement_continuation", path)
    if spec is None or spec.loader is None:
        raise MeasurementWakeBlocked("MEASUREMENT_CONTINUATION_MODULE_UNAVAILABLE")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _control_route():
    config = _load_json(ROUTE_CONFIG, "MEASUREMENT_ROUTE_CONFIG_INVALID")
    route_task_id = str(config.get("route_task_id") or "").strip()
    route = _load_json(ROUTES / f"{route_task_id}.json", "MEASUREMENT_ROUTE_BINDING_INVALID")
    chat_id = str(route.get("chat_id") or "").strip()
    if not route_task_id or not chat_id:
        raise MeasurementWakeBlocked("MEASUREMENT_ROUTE_INVALID")
    return route_task_id, chat_id


def ensure_measurement_continuation(supervisor, overlay: dict) -> dict:
    if not isinstance(overlay, dict) or overlay.get("queue_status") != "MEASUREMENT_READY":
        raise MeasurementWakeBlocked("MEASUREMENT_READY_REQUIRED")
    cid = str(overlay.get("candidate_id") or "")
    auth = overlay.get("measurement_authorization")
    if not cid or not isinstance(auth, dict) or auth.get("authorized") is not True:
        raise MeasurementWakeBlocked("MEASUREMENT_AUTHORIZATION_MISSING")
    if auth.get("scope") != "READ_ONLY_PROSPECTIVE_MARKET_DATA":
        raise MeasurementWakeBlocked("MEASUREMENT_SCOPE_INVALID")
    if any(overlay.get(flag) is not False for flag in ("live_trading", "paid_actions", "wallet_actions")):
        raise MeasurementWakeBlocked("MEASUREMENT_UNSAFE_FLAGS")
    if auth.get("order_submission") is not False or auth.get("live_trading") is not False:
        raise MeasurementWakeBlocked("MEASUREMENT_ORDER_PATH_FORBIDDEN")
    reviews = overlay.get("astra_reviews")
    approval = reviews.get("PREMEASUREMENT") if isinstance(reviews, dict) else None
    if not isinstance(approval, dict) or approval.get("decision") != "APPROVE" or approval.get("reviewer_model") != "GPT-6 Astra":
        raise MeasurementWakeBlocked("ASTRA_PREMEASUREMENT_APPROVAL_REQUIRED")
    if approval.get("ref") != auth.get("astra_premeasurement_review_ref"):
        raise MeasurementWakeBlocked("ASTRA_PREMEASUREMENT_REF_MISMATCH")

    route_task_id, chat_id = _control_route()
    identity = {
        "candidate_id": cid,
        "originating_task_id": overlay.get("originating_task_id"),
        "completion_hash": overlay.get("completion_hash"),
        "validation_hash": overlay.get("validation_hash"),
        "astra_review": auth.get("astra_premeasurement_review_ref"),
        "scope": auth.get("scope"),
    }
    digest = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    source_task_id = "MEASURE-" + digest[:40]
    context = (
        "PREDICTION_PROSPECTIVE_MEASUREMENT_REQUEST_V1\n"
        f"candidate_id={cid}\n"
        "required_builder_policy=HIGHEST_AVAILABLE_GPT\n"
        "economic_policy=ANY_POSITIVE_NET_EDGE_COUNTS\n"
        "minimum_net_profit_eur=0.0\n"
        "measurement_scope=READ_ONLY_PROSPECTIVE_MARKET_DATA\n"
        "This is NOT authorization to trade. No orders, cancellations, wallets, funds, paid APIs or live trading. "
        "Use the strongest GPT builder actually available to this builder session; if the session cannot satisfy that policy, choose BLOCKED. "
        "Inspect current canonical GitHub source and the exact Astra PREMEASUREMENT review before changing anything. "
        "Deploy/activate only the smallest bounded read-only or shadow collector needed to prospectively measure the preregistered hypothesis on current public market data. "
        "Freeze sample/trigger/fees/slippage/fill assumptions before observing outcomes. Small profit is not a reason to stop: any strictly positive NET executable euro edge is worth measuring. "
        "Use project task + DEV manifest + existing command bus for build/deploy/test operations, preserving live_trading=false, paid_actions=false, wallet_actions=false. "
        "Require compile/unit/integration/runtime-canary tests appropriate to the collector. "
        "When the preregistered measurement completes, write immutable result evidence under knowledge/experiment_results/, including gross result, all costs, net EUR result, sample size, misses/fills assumptions and falsification outcome; "
        "then update the candidate source to RESULT_READY for Director analysis while preserving scientific_status=NO_PROVEN_EDGE until all proof gates pass. "
        "Do not claim an edge merely because one observation is positive."
    )
    continuation = _load_continuation()
    record = continuation.start_external_continuation(
        data_dir=BRIDGE_DATA,
        source_task_id=source_task_id,
        chat_id=chat_id,
        expected_route_task_id=route_task_id,
        context_message=context,
        source_kind="PROSPECTIVE_MEASUREMENT_DEPLOYMENT",
    )
    audit = {
        "schema": SCHEMA,
        **identity,
        "source_task_id": source_task_id,
        "continuation_id": record["continuation_id"],
        "control_route_task_id": route_task_id,
        "required_builder_policy": "HIGHEST_AVAILABLE_GPT",
        "economic_policy": "ANY_POSITIVE_NET_EDGE_COUNTS",
        "minimum_net_profit_eur": 0.0,
        "measurement_scope": "READ_ONLY_PROSPECTIVE_MARKET_DATA",
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
    }
    audit_path = P(supervisor.root) / "measurement_wakes" / f"{source_task_id}.json"
    if audit_path.exists():
        if _load_json(audit_path, "MEASUREMENT_WAKE_AUDIT_INVALID") != audit:
            raise MeasurementWakeBlocked("MEASUREMENT_WAKE_AUDIT_CONFLICT")
    else:
        from supervisor import atomic
        atomic(audit_path, audit)
    return {
        "candidate_id": cid,
        "source_task_id": source_task_id,
        "continuation_id": record["continuation_id"],
        "continuation_state": record["state"],
        "audit_ref": str(audit_path.relative_to(P(supervisor.root))),
    }
