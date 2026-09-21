from __future__ import annotations

from pathlib import Path
from datetime import datetime
import importlib.util
import json
import sys
import time


ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {name} from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.modules.pop(spec.name, None)
        raise
    return mod


def current_run_id(now: datetime) -> str:
    return "hourly-" + now.strftime("%Y%m%dT%H0000%z")


def write_status(run_id: str, value: dict) -> Path:
    out = ROOT / "knowledge/ai_exchange/status" / f"{run_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tmp.replace(out)
    return out


def browser_fallback(now: datetime, run_id: str, reason: str) -> dict:
    stamp = now.strftime("%Y%m%dT%H00%z")
    iid = "hourly-research-" + stamp
    idir = Path.home() / ".local/state/prediction-research/incidents"
    idir.mkdir(parents=True, exist_ok=True)
    path = idir / (iid + "__HOURLY_RESEARCH_WAKE.json")
    if not path.exists():
        ts = time.time()
        data = {
            "incident_id": iid,
            "task_id": iid,
            "run_id": run_id,
            "reason": "HOURLY_RESEARCH_WAKE",
            "detail": (
                "Git AI exchange was unavailable; browser bridge is fallback only. "
                "Run the hourly autonomous prediction-market research director. "
                "Use only free/public sources. Route evidence through specialist "
                "agents, falsification, reproduction and publish the hourly report "
                "to Git. NO_PROVEN_EDGE is valid. No live trading, paid actions or "
                "wallet actions. Transport failure: " + reason[:500]
            ),
            "status": "OPEN",
            "deliver_to_chat": True,
            "first_seen_at": ts,
            "last_seen_at": ts,
            "automatic_action": "RESEARCH_WAKE_FALLBACK_ONLY",
            "running_task_killed": False,
            "paid_action": False,
            "live_trading_action": False,
            "wallet_action": False,
        }
        path.write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return {
        "used": True,
        "incident": str(path),
        "reason": reason,
    }


def main() -> int:
    now = datetime.now().astimezone()
    run_id = current_run_id(now)

    contract = load_module(
        "prediction_ai_work_exchange_wake",
        ROOT / "control/hourly/ai_work_exchange.py",
    )
    transport = load_module(
        "prediction_git_ai_exchange_wake",
        ROOT / "control/hourly/git_ai_exchange.py",
    )

    # Pull completed specialist work first. The receiver is idempotent and
    # re-runs orchestration after application. A transport outage never widens
    # authority and does not block the local research cycle.
    ingest = transport.safe_ingest_remote_responses()

    bundle_path = ROOT / "knowledge/runs" / f"{run_id}-ai-work-bundle.json"
    publish: dict
    request_path: str | None = None

    if bundle_path.exists():
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        request, local_request_path = contract.build_and_write(bundle)
        request_path = str(local_request_path.relative_to(ROOT))
        publish = transport.safe_publish_request(request)
    else:
        publish = {
            "ok": False,
            "status": "NO_CURRENT_BUNDLE",
            "run_id": run_id,
            "published": False,
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
        }

    fallback = {"used": False}
    publish_status = publish.get("status")
    no_ai_work = publish_status == "NO_WORK"
    git_delivered = publish_status in {"PUBLISHED", "ALREADY_PUBLISHED"}

    # The old browser bridge is deliberately only a fallback transport now.
    # A no-work cycle requires no wake at all.
    if not no_ai_work and not git_delivered:
        fallback = browser_fallback(
            now,
            run_id,
            str(publish.get("error") or publish_status),
        )

    status = {
        "schema": "PVA_AI_WAKE_STATUS_V2",
        "run_id": run_id,
        "transport_preference": "git",
        "browser_bridge_required": False,
        "ingest": ingest,
        "publish": publish,
        "local_request_ref": request_path,
        "browser_fallback": fallback,
        "economic_conclusion": "NO_PROVEN_EDGE",
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "openai_api": False,
    }
    status_path = write_status(run_id, status)
    status["status_ref"] = str(status_path.relative_to(ROOT))
    print(json.dumps(status, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
