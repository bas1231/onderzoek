"""Local-only request transport; never invokes Git, network, or model APIs.

Actual browser delivery and response application remain independently evidenced.
The enclosing qualification runner supplies filesystem/network confinement.
"""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def publish_request(request):
    contract = load_module("local_exchange_contract", ROOT / "control/hourly/ai_work_exchange.py")
    request = contract.validate_request(request)
    receiver = load_module("local_exchange_receiver", ROOT / "control/hourly/ai_response_receiver.py")
    run_id = receiver.safe_run_id(request["run_id"])
    path = ROOT / "knowledge/ai_exchange/requests" / f"{run_id}.json"
    # build_and_write must have persisted exactly this immutable request first.
    stored = contract.validate_request(json.loads(path.read_text()))
    if stored != request:
        raise ValueError("local request provenance mismatch")
    return {
        "ok": True, "run_id": run_id,
        "status": "DISPATCH_PENDING" if request["work_items"] else "NO_WORK",
        "published": False, "model_roundtrip_proven": False,
        "request_path": str(path.relative_to(ROOT)),
        "live_trading": False, "wallet_actions": False,
        "paid_actions": False, "openai_api": False,
    }


def ingest_local_responses(*, limit=32):
    contract = load_module("local_exchange_contract_ingest", ROOT / "control/hourly/ai_work_exchange.py")
    receiver = load_module("local_exchange_receiver_ingest", ROOT / "control/hourly/ai_response_receiver.py")
    applied, errors = [], []
    inbox = ROOT / "knowledge/ai_exchange/responses"
    for path in sorted(inbox.glob("*.json"))[-limit:]:
        try:
            envelope = json.loads(path.read_text())
            if not isinstance(envelope, dict) or envelope.get("schema") != "PVA_AI_EXCHANGE_RESPONSE_V1":
                raise ValueError("invalid local response envelope")
            run_id = receiver.safe_run_id(envelope.get("run_id"))
            if path.name != run_id + ".json":
                raise ValueError("response filename/run mismatch")
            request_path = ROOT / "knowledge/ai_exchange/requests" / f"{run_id}.json"
            request = contract.validate_request(json.loads(request_path.read_text()))
            if request["request_sha256"] != envelope.get("request_sha256"):
                raise ValueError("response request provenance mismatch")
            result = receiver.receive({"run_id": run_id, "response": envelope.get("response")})
            applied.append(result)
        except Exception as exc:
            errors.append({"path": str(path.relative_to(ROOT)), "error_type": type(exc).__name__, "error": str(exc)[:1000]})
    return {"ok": not errors, "status": "RESPONSE_REJECTED" if errors else ("APPLIED" if applied else "NO_APPLICABLE_RESPONSES"), "applied": applied, "errors": errors}
