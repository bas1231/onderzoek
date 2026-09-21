from __future__ import annotations

import importlib.util
import json
import py_compile
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path.cwd()
TARGET = ROOT / "control/browser_bridge.py"


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=check)


# Always refresh the remote source of truth first.
fetch = run("git", "fetch", "origin", "main", check=False)
if fetch.returncode != 0:
    print("FETCH_ORIGIN_MAIN=FAIL")
    print(fetch.stderr.strip())
    raise SystemExit(20)
print("FETCH_ORIGIN_MAIN=PASS")

# Reuse the already-reviewed E379 result-priority installer from origin/main.
installer_bytes = subprocess.run(
    ["git", "show", "origin/main:control/jobs/install_result_priority_e379.py"],
    cwd=ROOT,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    check=True,
).stdout
with tempfile.TemporaryDirectory() as td:
    installer = Path(td) / "install_result_priority_e379.py"
    installer.write_bytes(installer_bytes)
    rc = subprocess.run([sys.executable, str(installer)], cwd=ROOT).returncode
    if rc != 0:
        print(f"E379_INSTALL=FAIL:{rc}")
        raise SystemExit(rc)
print("E379_INSTALL=PASS")

# Make ordinary /ack durable/idempotent for real results and incident items.
text = TARGET.read_text(encoding="utf-8")
old = '''def acknowledge(task_id: str) -> dict:\n    state = load_state()\n\n    if task_id not in state.get("bridge_tasks", []):\n        return {\n            "ok": False,\n            "error": "unknown bridge task",\n        }\n\n    acked = state.setdefault("acked", [])\n\n    if task_id not in acked:\n        acked.append(task_id)\n\n    save_state(state)\n\n    lifecycle_update(\n        task_id,\n        "ACKED",\n        "browser acknowledged result",\n    )\n\n    return {\n        "ok": True,\n        "task_id": task_id,\n    }\n'''
new = '''def acknowledge(task_id: str) -> dict:\n    state = load_state()\n\n    if not TASK_ID_RE.fullmatch(task_id):\n        return {\n            "ok": False,\n            "error": "invalid task_id",\n        }\n\n    bridge_tasks = state.setdefault("bridge_tasks", [])\n    known = task_id in bridge_tasks\n    result_exists = (RESULTS / task_id / "RESULT.json").exists()\n    incident_item = task_id.startswith("INCIDENT-")\n\n    if not (known or result_exists or incident_item):\n        return {\n            "ok": False,\n            "error": "unknown bridge task",\n        }\n\n    if task_id not in bridge_tasks:\n        bridge_tasks.append(task_id)\n\n    acked = state.setdefault("acked", [])\n\n    if task_id not in acked:\n        acked.append(task_id)\n\n    save_state(state)\n\n    lifecycle_update(\n        task_id,\n        "ACKED",\n        "browser acknowledged result",\n    )\n\n    return {\n        "ok": True,\n        "task_id": task_id,\n        "recovered": not known,\n    }\n'''
if old in text:
    TARGET.write_text(text.replace(old, new, 1), encoding="utf-8")
elif '"recovered": not known' not in text:
    raise SystemExit("ACK_PATCH_ANCHOR_MISSING")

py_compile.compile(str(TARGET), doraise=True)
print("ACK_PATCH_COMPILE=PASS")

# Prospective unit probe for an incident ACK that is not yet present in bridge_tasks.
spec = importlib.util.spec_from_file_location("bridge_e381_probe", TARGET)
if spec is None or spec.loader is None:
    raise SystemExit("BRIDGE_IMPORT_SPEC_FAILED")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)
with tempfile.TemporaryDirectory() as td:
    tmp = Path(td)
    mod.STATE_FILE = tmp / "bridge_state.json"
    mod.RESULTS = tmp / "results"
    mod.RESULTS.mkdir(parents=True, exist_ok=True)
    mod.lifecycle_update = lambda *args, **kwargs: None
    mod.STATE_FILE.write_text(json.dumps({"bridge_tasks": [], "acked": []}), encoding="utf-8")
    probe_id = "INCIDENT-E381-ACK-PROBE"
    response = mod.acknowledge(probe_id)
    state = json.loads(mod.STATE_FILE.read_text(encoding="utf-8"))
    assert response.get("ok") is True, response
    assert probe_id in state.get("acked", []), state
    second = mod.acknowledge(probe_id)
    assert second.get("ok") is True, second
print("INCIDENT_ACK_PROBE=PASS")

# Commit only the bridge repair if it changed.
subprocess.run(["git", "add", "control/browser_bridge.py"], cwd=ROOT, check=True)
staged = run("git", "diff", "--cached", "--quiet", check=False)
if staged.returncode != 0:
    subprocess.run(
        ["git", "commit", "-m", "fix: make bridge result ack durable"],
        cwd=ROOT,
        check=True,
    )
print("BRIDGE_REPAIR_COMMIT=PASS")

subprocess.run(
    ["systemctl", "--user", "restart", "prediction-research-browser-bridge.service"],
    cwd=ROOT,
    check=True,
)
health = subprocess.run(
    [
        sys.executable,
        "-c",
        "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8765/health', timeout=5); print(r.status); assert r.status==200",
    ],
    cwd=ROOT,
    text=True,
    capture_output=True,
    check=True,
)
print("BRIDGE_RESTART=PASS")
print("HEALTH_200=PASS")

# Report exact git state; do not destructively sync or discard local work.
run("git", "fetch", "origin", "main", check=False)
branch = run("git", "branch", "--show-current").stdout.strip()
head = run("git", "rev-parse", "HEAD").stdout.strip()
remote = run("git", "rev-parse", "origin/main").stdout.strip()
divergence = run("git", "rev-list", "--left-right", "--count", "HEAD...origin/main").stdout.strip()
status = run("git", "status", "--porcelain=v1").stdout
print("BRANCH=" + branch)
print("HEAD=" + head)
print("ORIGIN_MAIN=" + remote)
print("HEAD_VS_ORIGIN_MAIN=" + divergence)
print("DIRTY_COUNT=" + str(len([line for line in status.splitlines() if line.strip()])))
if status.strip():
    print("STATUS_PORCELAIN_BEGIN")
    print(status.rstrip())
    print("STATUS_PORCELAIN_END")
print("CONTROL_PLANE_REPAIR_E381=PASS")
