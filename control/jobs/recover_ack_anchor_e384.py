from __future__ import annotations

import pathlib
import py_compile
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path.cwd()
TARGET = ROOT / "control/browser_bridge.py"
TASK_ID = sys.argv[1] if len(sys.argv) > 1 else ""


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=check)


def structural_ack_patch() -> None:
    text = TARGET.read_text(encoding="utf-8")
    if '"recovered": not known' in text:
        print("ACK_STRUCTURAL_PATCH=ALREADY_PRESENT")
        return

    match = re.search(r"(?m)^def acknowledge\(task_id: str\) -> dict:\n", text)
    if match is None:
        print("ACK_STRUCTURAL_PATCH=FAIL:NO_FUNCTION")
        raise SystemExit(60)

    start = match.start()
    next_def = re.search(r"(?m)^def [A-Za-z_][A-Za-z0-9_]*\(", text[match.end():])
    if next_def is None:
        end = len(text)
    else:
        end = match.end() + next_def.start()

    replacement = '''def acknowledge(task_id: str) -> dict:\n    state = load_state()\n\n    if not TASK_ID_RE.fullmatch(task_id):\n        return {\n            "ok": False,\n            "error": "invalid task_id",\n        }\n\n    bridge_tasks = state.setdefault("bridge_tasks", [])\n    known = task_id in bridge_tasks\n    result_exists = (RESULTS / task_id / "RESULT.json").exists()\n    incident_item = task_id.startswith("INCIDENT-")\n\n    if not (known or result_exists or incident_item):\n        return {\n            "ok": False,\n            "error": "unknown bridge task",\n        }\n\n    if task_id not in bridge_tasks:\n        bridge_tasks.append(task_id)\n\n    acked = state.setdefault("acked", [])\n    if task_id not in acked:\n        acked.append(task_id)\n\n    save_state(state)\n    lifecycle_update(\n        task_id,\n        "ACKED",\n        "browser acknowledged result",\n    )\n\n    return {\n        "ok": True,\n        "task_id": task_id,\n        "recovered": not known,\n    }\n\n\n'''
    TARGET.write_text(text[:start] + replacement + text[end:], encoding="utf-8")
    py_compile.compile(str(TARGET), doraise=True)
    print("ACK_STRUCTURAL_PATCH=PASS")


branch = run("git", "branch", "--show-current").stdout.strip()
if branch != "main":
    print("BRANCH_CHECK=FAIL:" + branch)
    raise SystemExit(61)
print("BRANCH_CHECK=PASS")

structural_ack_patch()

fetch = run("git", "fetch", "origin", "main", check=False)
if fetch.returncode != 0:
    print("FETCH_ORIGIN_MAIN=FAIL")
    print(fetch.stderr.strip())
    raise SystemExit(62)
print("FETCH_ORIGIN_MAIN=PASS")

script_bytes = subprocess.run(
    ["git", "show", "origin/main:control/jobs/recover_bridge_e383.py"],
    cwd=ROOT,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    check=True,
).stdout
with tempfile.TemporaryDirectory() as td:
    script = pathlib.Path(td) / "recover_bridge_e383.py"
    script.write_bytes(script_bytes)
    rc = subprocess.run([sys.executable, str(script), TASK_ID], cwd=ROOT).returncode
    if rc != 0:
        print(f"E383_CHAIN=FAIL:{rc}")
        raise SystemExit(rc)
print("E383_CHAIN=PASS")
print("CONTROL_PLANE_RECOVER_SYNC_E384=PASS")
