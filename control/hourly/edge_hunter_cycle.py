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
SELFHEAL_STATUS = STATE / "command-bus-selfheal-latest.json"


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


def run_optional_command_bus_selfheal() -> None:
    """Repair the user-level command bus without making hourly research depend on it.

    runtime_sync.py fast-forwards main before this wrapper starts, so this hook is
    an independent recovery path when the command-bus poller itself is stale or
    stopped. It is deliberately bounded to the repository-owned self-heal helper.
    """
    helper = ROOT / "control/hourly/command_bus_selfheal.py"
    if not helper.is_file():
        print("COMMAND_BUS_SELFHEAL=ABSENT")
        return
    try:
        proc = subprocess.run(
            [str(ROOT / ".venv/bin/python"), str(helper)],
            cwd=str(ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=240,
        )
        output = (proc.stdout or "").strip()
        if len(output) > 6000:
            output = output[-6000:]
        print("COMMAND_BUS_SELFHEAL_RC", proc.returncode)
        if output:
            print("COMMAND_BUS_SELFHEAL_OUTPUT", output)
    except Exception as exc:
        # Do not break the research cycle because infrastructure recovery failed.
        print("COMMAND_BUS_SELFHEAL_EXCEPTION", type(exc).__name__, str(exc)[:1000])


def read_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def append_selfheal_evidence(run_id: str) -> None:
    """Attach bounded local recovery evidence to the normal hourly artifacts.

    This does not publish by itself. It only makes the already-existing hourly
    checkpoint/report path able to show whether self-heal and the E008 canary
    actually completed.
    """
    status = read_json(SELFHEAL_STATUS)
    if not status:
        return

    run_path = ROOT / "knowledge/runs" / f"{run_id}.json"
    current = read_json(run_path)
    if current is not None:
        current["command_bus_selfheal"] = status
        tmp = run_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(run_path)

    report_path = ROOT / "hourly-reports" / f"{run_id}.md"
    marker = "## Command-bus self-heal"
    existing = report_path.read_text(encoding="utf-8", errors="replace") if report_path.exists() else ""
    if marker in existing:
        return
    canary = status.get("canary") if isinstance(status.get("canary"), dict) else {}
    with report_path.open("a", encoding="utf-8") as handle:
        handle.write("\n" + marker + "\n\n")
        handle.write("Status: **" + str(status.get("status")) + "**\n")
        handle.write("Canary task: `" + str(status.get("canary_task_id")) + "`\n")
        handle.write("Timer active: " + str(status.get("timer_active")) + "\n")
        handle.write("Poll-once rc: " + str(status.get("poll_once_rc")) + "\n")
        handle.write("Command state: " + str(canary.get("task_state_status")) + "\n")
        handle.write("DEV receipt finished: " + str(canary.get("receipt_finished")) + "\n")
        handle.write("DEV receipt exit 0: " + str(canary.get("receipt_exit_zero")) + "\n")
        handle.write("E2E PASS marker: " + str(canary.get("receipt_has_pass_marker")) + "\n")
        handle.write("Safety: live_trading=false, paid_actions=false, wallet_actions=false, remote_git_write=false.\n")


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
    # Independent bootstrap path for a broken/stale command-bus poller. This is
    # intentionally before the normal research cycle and fail-soft for research.
    run_optional_command_bus_selfheal()

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
    append_selfheal_evidence(run_id)

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
