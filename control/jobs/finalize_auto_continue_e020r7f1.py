from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT = Path.cwd()
BRIDGE = ROOT / "control/browser_bridge.py"
TEST = ROOT / "tests/bridge/test_control_auto_continue.py"
LEDGER = ROOT / "control/BRIDGE_INCIDENT_LEDGER.md"


def run(*args: str):
    return subprocess.run(
        list(args),
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


text = BRIDGE.read_text(encoding="utf-8")
required = [
    "PVA_CONTROL_CONTINUE_V1",
    "def _queue_control_continue(",
    "def _next_control_continue_item(",
    "_queue_control_continue(state, task_id, \"RESULT_ACKED\")",
]
missing = [token for token in required if token not in text]
if missing:
    raise SystemExit("AUTO_CONTINUE_PATCH_NOT_PRESENT: " + ", ".join(missing))

compile_result = run(
    sys.executable,
    "-m",
    "py_compile",
    "control/browser_bridge.py",
)
if compile_result.returncode != 0:
    print(compile_result.stdout)
    print(compile_result.stderr, file=sys.stderr)
    raise SystemExit("PY_COMPILE_FAILED")

pytest_result = run(
    sys.executable,
    "-m",
    "pytest",
    "-q",
    "tests/bridge/test_control_auto_continue.py",
)
print(pytest_result.stdout)
print(pytest_result.stderr)
if pytest_result.returncode != 0:
    raise SystemExit("PYTEST_FAILED")

stage = [
    "control/browser_bridge.py",
    "tests/bridge/test_control_auto_continue.py",
]
if LEDGER.exists():
    stage.append("control/BRIDGE_INCIDENT_LEDGER.md")

add_result = run("git", "add", *stage)
if add_result.returncode != 0:
    print(add_result.stderr, file=sys.stderr)
    raise SystemExit("GIT_ADD_FAILED")

staged = run("git", "diff", "--cached", "--quiet")
if staged.returncode != 0:
    commit_result = run(
        "git",
        "commit",
        "-m",
        "fix: activate durable control auto continuation",
    )
    print(commit_result.stdout)
    print(commit_result.stderr)
    if commit_result.returncode != 0:
        raise SystemExit("GIT_COMMIT_FAILED")

restart = run(
    "systemctl",
    "--user",
    "restart",
    "prediction-research-browser-bridge.service",
)
if restart.returncode != 0:
    print(restart.stderr, file=sys.stderr)
    raise SystemExit("BRIDGE_RESTART_FAILED")

time.sleep(2)
with urllib.request.urlopen(
    "http://127.0.0.1:8765/health",
    timeout=5,
) as response:
    body = response.read().decode()
    if response.status != 200:
        print(body, file=sys.stderr)
        raise SystemExit("BRIDGE_HEALTH_FAILED")

head = run("git", "rev-parse", "HEAD")
print("AUTO_CONTINUE_PATCH_PRESENT=PASS")
print("PY_COMPILE=PASS")
print("PYTEST=PASS")
print("OPTIONAL_LEDGER_STAGE=PASS")
print("BRIDGE_RESTART=PASS")
print("HEALTH_200=PASS")
print("HEAD=" + head.stdout.strip())
