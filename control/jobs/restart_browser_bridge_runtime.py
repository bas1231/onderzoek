#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
SERVICE = "prediction-research-browser-bridge.service"
EXPECTED_SCRIPT = str(ROOT / "control/browser_bridge.py")


def run(*args: str, timeout: int = 20):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)


def emit(payload: dict, code: int):
    payload.update({
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
        "openai_api": False,
    })
    print(json.dumps(payload, indent=2, sort_keys=True))
    raise SystemExit(code)


# Ensure the on-disk source contains the runtime-attestation invariant before
# restarting the long-running service.
source = ROOT / "control/browser_bridge.py"
if not source.is_file():
    emit({"status": "BLOCKED", "reason": "BRIDGE_SOURCE_MISSING"}, 2)
text = source.read_text(encoding="utf-8")
required_tokens = [
    "_LOADED_BRIDGE_COMMIT",
    "BRIDGE_RUNTIME_STALE_REEXEC_SCHEDULED",
    "_schedule_bridge_reexec",
]
missing = [token for token in required_tokens if token not in text]
if missing:
    emit({
        "status": "BLOCKED",
        "reason": "RUNTIME_ATTESTATION_SOURCE_NOT_PRESENT",
        "missing": missing,
    }, 3)

before = run("systemctl", "--user", "show", SERVICE, "-p", "ActiveState", "-p", "SubState", "-p", "ExecStart")
if before.returncode != 0:
    emit({
        "status": "BLOCKED",
        "reason": "SERVICE_SHOW_FAILED",
        "stderr": before.stderr[-3000:],
    }, 4)

restart = run("systemctl", "--user", "restart", SERVICE, timeout=30)
if restart.returncode != 0:
    emit({
        "status": "BLOCKED",
        "reason": "SERVICE_RESTART_FAILED",
        "stderr": restart.stderr[-3000:],
    }, 5)

time.sleep(0.8)
after = run("systemctl", "--user", "show", SERVICE, "-p", "ActiveState", "-p", "SubState", "-p", "ExecStart")
if after.returncode != 0:
    emit({
        "status": "BLOCKED",
        "reason": "SERVICE_POST_RESTART_SHOW_FAILED",
        "stderr": after.stderr[-3000:],
    }, 6)

props = {}
for line in after.stdout.splitlines():
    if "=" in line:
        key, value = line.split("=", 1)
        props[key] = value

if props.get("ActiveState") != "active" or props.get("SubState") != "running":
    emit({
        "status": "BLOCKED",
        "reason": "SERVICE_NOT_RUNNING_AFTER_RESTART",
        "service": props,
    }, 7)

if EXPECTED_SCRIPT not in props.get("ExecStart", ""):
    emit({
        "status": "BLOCKED",
        "reason": "UNEXPECTED_BRIDGE_EXECSTART",
        "expected_script": EXPECTED_SCRIPT,
        "service": props,
    }, 8)

health_obj = None
last_error = None
for _ in range(20):
    try:
        with urlopen("http://127.0.0.1:8765/health", timeout=1.0) as response:
            body = response.read().decode("utf-8", errors="replace")
            if response.status == 200:
                health_obj = json.loads(body)
                break
    except Exception as exc:
        last_error = f"{type(exc).__name__}: {exc}"
        time.sleep(0.2)

if not isinstance(health_obj, dict):
    emit({
        "status": "BLOCKED",
        "reason": "BRIDGE_HEALTH_NOT_READY_AFTER_RESTART",
        "last_error": last_error,
        "service": props,
    }, 9)

emit({
    "status": "PASS",
    "service": {
        "ActiveState": props.get("ActiveState"),
        "SubState": props.get("SubState"),
        "ExecStart_matches_expected": True,
    },
    "health_status": health_obj.get("status"),
    "health_git_head": health_obj.get("git_head"),
    "runtime_attestation_source_present": True,
}, 0)
