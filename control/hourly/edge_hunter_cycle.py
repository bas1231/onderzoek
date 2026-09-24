from __future__ import annotations

from pathlib import Path
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
STATE = Path.home() / ".local/state/prediction-research"
CYCLE_RECEIPT = STATE / "scheduled-cycle-latest.json"
GIT_CHECKPOINT = STATE / "git-checkpoint-latest.json"


def load_hourly_cycle():
    path = ROOT / "control/hourly/hourly_cycle.py"
    spec = importlib.util.spec_from_file_location("prediction_hourly_cycle", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load hourly cycle from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.modules.pop(spec.name, None)
        raise
    return mod


def latest_canonical_run_id() -> str:
    """Return the newest canonical hourly manifest, never a derivative JSON file."""
    candidates = []
    for path in (ROOT / "knowledge/runs").glob("hourly-*.json"):
        stem = path.stem
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("run_id") == stem and data.get("status") is not None:
            candidates.append(path)
    if not candidates:
        raise RuntimeError("no canonical hourly run manifest found")
    newest = max(candidates, key=lambda p: p.stat().st_mtime)
    return newest.stem


def run_required_checkpoint(script: str, label: str, timeout: int = 180) -> None:
    proc = subprocess.run(
        [str(ROOT / ".venv/bin/python"), str(ROOT / script)],
        check=False,
        timeout=timeout,
        cwd=str(ROOT),
    )
    print(label, proc.returncode)
    if proc.returncode != 0:
        raise RuntimeError(f"{label} failed with rc={proc.returncode}")


def read_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def write_cycle_receipt(run_id: str) -> None:
    """Persist one bounded correlation receipt after every required checkpoint passed.

    This proves completion of this local wrapper invocation only. It deliberately
    does not claim that the browser bridge or exchange poller is continuously UP.
    """
    checkpoint = read_json(GIT_CHECKPOINT)
    payload = {
        "schema": "PVA_SCHEDULED_CYCLE_RECEIPT_V1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "status": "COMPLETED",
        "git_checkpoint_status": (checkpoint or {}).get("status"),
        "git_checkpoint_head": (checkpoint or {}).get("head"),
        "claims": {
            "scheduled_wrapper_completed": True,
            "required_checkpoints_completed": True,
            "browser_bridge_running": False,
            "runtime_exchange_running": False,
        },
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "openai_api": False,
    }
    STATE.mkdir(parents=True, exist_ok=True)
    tmp = CYCLE_RECEIPT.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(CYCLE_RECEIPT)


def main() -> int:
    # Do not use runpy(..., run_name='__main__') here. hourly_cycle.py ends in
    # SystemExit(main()), which used to terminate this wrapper with rc=0 before
    # Edge Hunter and durable checkpoints ever ran.
    hourly = load_hourly_cycle()
    cycle_rc = int(hourly.main())
    if cycle_rc == 75:
        print("HOURLY_CYCLE_COOLDOWN")
        return 75
    if cycle_rc != 0:
        raise RuntimeError(f"hourly cycle failed with rc={cycle_rc}")

    run_id = latest_canonical_run_id()
    sys.path.insert(0, str(ROOT / "control/edge_hunter"))
    from director import prepare

    packet = prepare(run_id)
    print("EDGE_HUNTER_PACKET", packet)

    run_required_checkpoint(
        "control/jobs/hourly_asset_fill_checkpoint_e354.py",
        "ASSET_FILL_CHECKPOINT_RC",
    )
    run_required_checkpoint(
        "control/jobs/hourly_kwi_full_station_checkpoint_e371.py",
        "KWI_FULL_STATION_CHECKPOINT_RC",
    )
    run_required_checkpoint(
        "control/hourly/git_checkpoint.py",
        "GIT_CHECKPOINT_RC",
    )
    write_cycle_receipt(run_id)
    print("SCHEDULED_CYCLE_RECEIPT", run_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
