from __future__ import annotations

import importlib.util
import json
import os
import py_compile
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
HOME = Path.home()
SOURCE = ROOT / "control/bridge_commands/command_bus_poller.py"
RUNTIME = HOME / ".local/share/prediction-command-bus/command_bus_poller.py"
STATE_DIR = HOME / ".local/state/prediction-research"
STATUS_PATH = STATE_DIR / "command-bus-selfheal-latest.json"
BUS_TASK_STATE = HOME / ".local/state/prediction-command-bus/tasks"
DEV_RECEIPTS = HOME / ".local/share/prediction-chat-bridge/dev-task-receipts"
CANARY_TASK_ID = "DEV-PRED-COMMAND-BUS-HEADLESS-CANARY-20261001-E008"


class SelfHealError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(argv: list[str], timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=timeout,
    )


def atomic_write(path: Path, data: bytes, mode: int = 0o755) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, mode)
        os.replace(tmp_name, path)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def save_status(status: str, **extra: Any) -> dict[str, Any]:
    payload = {
        "schema": "PVA_COMMAND_BUS_SELFHEAL_V1",
        "timestamp_utc": now_iso(),
        "status": status,
        "canary_task_id": CANARY_TASK_ID,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "credential_access": False,
        "remote_git_write": False,
        **extra,
    }
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATUS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(STATUS_PATH)
    return payload


def load_poller_module(path: Path):
    spec = importlib.util.spec_from_file_location("prediction_command_bus_selfheal_canary", path)
    if spec is None or spec.loader is None:
        raise SelfHealError("cannot import poller")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.modules.pop(spec.name, None)
    return mod


def source_canary(path: Path) -> None:
    py_compile.compile(str(path), doraise=True)
    mod = load_poller_module(path)
    command = {
        "schema": "PREDICTION_BRIDGE_COMMAND_V1",
        "task_id": "DEV-PRED-SELFHEAL-SOURCE-CANARY",
        "action": "SIX_AI_HEALTH",
        "created_at_utc": "2026-10-01T07:00:00Z",
        "delivery_mode": "headless",
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "intelligence_tier": "C",
        "issuer": {"model": "GPT-5.6 Sol", "reasoning_level": "UNAVAILABLE_TO_RUNTIME"},
    }
    ok, reason = mod.validate_command(command)
    if not ok or reason != "OK":
        raise SelfHealError(f"headless source validation failed: {reason}")
    route, route_source = mod.resolve_route(command)
    if route_source != "headless" or not isinstance(route, dict):
        raise SelfHealError("headless source routing canary failed")


def ensure_service_started(unit: str) -> dict[str, Any]:
    active = run(["systemctl", "--user", "is-active", unit], timeout=20)
    before = active.stdout.strip()
    start_rc = None
    if active.returncode != 0:
        started = run(["systemctl", "--user", "start", unit], timeout=60)
        start_rc = started.returncode
    final = run(["systemctl", "--user", "is-active", unit], timeout=20)
    return {
        "unit": unit,
        "before": before,
        "start_rc": start_rc,
        "active": final.returncode == 0,
        "after": final.stdout.strip(),
    }


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def canary_evidence(wait_seconds: int = 120) -> dict[str, Any]:
    state_path = BUS_TASK_STATE / f"{CANARY_TASK_ID}.json"
    receipt_path = DEV_RECEIPTS / f"{CANARY_TASK_ID}.log"
    deadline = time.monotonic() + wait_seconds
    latest_state = None
    receipt_text = ""
    while time.monotonic() < deadline:
        latest_state = read_json(state_path)
        try:
            receipt_text = receipt_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            receipt_text = ""
        if "STATUS=FINISHED" in receipt_text and "EXIT_CODE=0" in receipt_text:
            break
        if latest_state and latest_state.get("status") in {"REJECTED", "FAILED", "AMBIGUOUS", "BLOCKED_ROUTE"}:
            break
        time.sleep(2)
    return {
        "task_state_status": (latest_state or {}).get("status"),
        "task_state_reason": (latest_state or {}).get("reason"),
        "receipt_finished": "STATUS=FINISHED" in receipt_text,
        "receipt_exit_zero": "EXIT_CODE=0" in receipt_text,
        "receipt_has_pass_marker": "HEADLESS_E2E_E008=PASS" in receipt_text,
    }


def main() -> int:
    try:
        if not SOURCE.is_file():
            raise SelfHealError(f"missing source poller: {SOURCE}")
        source_canary(SOURCE)
        source_bytes = SOURCE.read_bytes()
        runtime_changed = not RUNTIME.is_file() or RUNTIME.read_bytes() != source_bytes
        if runtime_changed:
            atomic_write(RUNTIME, source_bytes)
        source_canary(RUNTIME)

        daemon_reload = run(["systemctl", "--user", "daemon-reload"], timeout=30)
        if daemon_reload.returncode != 0:
            raise SelfHealError("systemd daemon-reload failed")

        router = ensure_service_started("prediction-chat-router.service")
        receiver = ensure_service_started("prediction-chat-command.service")

        timer_enable = run(
            ["systemctl", "--user", "enable", "--now", "prediction-command-bus.timer"],
            timeout=60,
        )
        timer_active = run(
            ["systemctl", "--user", "is-active", "prediction-command-bus.timer"],
            timeout=20,
        )
        poll_once = run(
            ["systemctl", "--user", "start", "prediction-command-bus.service"],
            timeout=180,
        )

        evidence = canary_evidence()
        installed_ok = (
            timer_enable.returncode == 0
            and timer_active.returncode == 0
            and router.get("active") is True
            and receiver.get("active") is True
            and poll_once.returncode == 0
        )
        canary_pass = (
            evidence.get("receipt_finished") is True
            and evidence.get("receipt_exit_zero") is True
            and evidence.get("receipt_has_pass_marker") is True
        )
        status = "PASS" if installed_ok and canary_pass else (
            "INSTALLED_CANARY_PENDING" if installed_ok else "BLOCKED"
        )
        payload = save_status(
            status,
            runtime_changed=runtime_changed,
            runtime_path=str(RUNTIME),
            router=router,
            receiver=receiver,
            timer_enable_rc=timer_enable.returncode,
            timer_active=timer_active.returncode == 0,
            poll_once_rc=poll_once.returncode,
            canary=evidence,
        )
        print(json.dumps(payload, sort_keys=True))
        return 0 if installed_ok else 2
    except Exception as exc:
        payload = save_status(
            "BLOCKED",
            error_type=type(exc).__name__,
            error=str(exc)[:2000],
        )
        print(json.dumps(payload, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
