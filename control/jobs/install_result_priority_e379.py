from pathlib import Path
import importlib.util
import json
import py_compile
import subprocess
import sys
import tempfile
import types

root = Path.cwd()
target = root / "control/browser_bridge.py"
text = target.read_text(encoding="utf-8")
marker = "# REAL_RESULTS_BEFORE_INCIDENTS_E379"
anchor = "    # RELIABILITY-E056: deliver local watchdog incidents\n"

priority_block = '''    # REAL_RESULTS_BEFORE_INCIDENTS_E379
    # A backlog of deliverable incidents must never starve completed executor
    # results. Surface any completed bridge task first; incidents remain the
    # fallback when no real task result is ready.
    for priority_task_id in bridge_tasks:
        if priority_task_id in acked:
            continue

        priority_result_dir = RESULTS / priority_task_id
        priority_result_file = priority_result_dir / "RESULT.json"

        if not priority_result_file.exists():
            continue

        priority_result = json.loads(priority_result_file.read_text())
        priority_stdout_file = priority_result_dir / "stdout.log"
        priority_stderr_file = priority_result_dir / "stderr.log"
        priority_stdout = (
            priority_stdout_file.read_text(errors="replace")[:20000]
            if priority_stdout_file.exists()
            else ""
        )
        priority_stderr = (
            priority_stderr_file.read_text(errors="replace")[:20000]
            if priority_stderr_file.exists()
            else ""
        )

        lifecycle_update(
            priority_task_id,
            "DELIVERED",
            "bridge outbox exposed result before incident backlog",
        )

        return {
            "task_id": priority_task_id,
            "result": priority_result,
            "stdout": priority_stdout,
            "stderr": priority_stderr,
            "git_head": git(
                "rev-parse",
                "--short",
                "HEAD",
            ).stdout.strip(),
        }

'''

if marker not in text:
    if anchor not in text:
        raise SystemExit("incident_anchor_missing")
    text = text.replace(anchor, priority_block + anchor, 1)
    target.write_text(text, encoding="utf-8")

py_compile.compile(str(target), doraise=True)

# Prospective local unit probe: a completed task must be returned even when the
# real incident directory contains old deliverable incidents.
sys.path.insert(0, str(root / "control"))
spec = importlib.util.spec_from_file_location("bridge_e379_probe", target)
if spec is None or spec.loader is None:
    raise SystemExit("bridge_import_spec_failed")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

with tempfile.TemporaryDirectory() as td:
    tmp = Path(td)
    mod.STATE_FILE = tmp / "bridge_state.json"
    mod.RESULTS = tmp / "results"
    mod.RESULTS.mkdir(parents=True, exist_ok=True)
    task_id = "E379-REAL-RESULT-PROBE"
    mod.STATE_FILE.write_text(json.dumps({"bridge_tasks": [task_id], "acked": []}), encoding="utf-8")
    result_dir = mod.RESULTS / task_id
    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / "RESULT.json").write_text(json.dumps({"task_id": task_id, "status": "completed", "exit_code": 0}), encoding="utf-8")
    (result_dir / "stdout.log").write_text("probe-ok\n", encoding="utf-8")
    mod.lifecycle_update = lambda *args, **kwargs: None
    mod.git = lambda *args, **kwargs: types.SimpleNamespace(stdout="probehead\n", returncode=0, stderr="")
    item = mod.next_outbox_item()
    assert item is not None, "no_outbox_item"
    assert item.get("task_id") == task_id, item
    assert item.get("result", {}).get("status") == "completed", item

subprocess.run(["git", "add", "control/browser_bridge.py"], check=True)
staged = subprocess.run(["git", "diff", "--cached", "--quiet"], check=False)
if staged.returncode != 0:
    subprocess.run(["git", "commit", "-m", "fix: prioritize real bridge results over incident backlog"], check=True)

subprocess.run(["systemctl", "--user", "restart", "prediction-research-browser-bridge.service"], check=True)
subprocess.run([sys.executable, "-c", "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8765/health', timeout=5); assert r.status==200"], check=True)

head = subprocess.run(["git", "rev-parse", "HEAD"], text=True, capture_output=True, check=True).stdout.strip()
print("RESULT_PRIORITY_PATCH=PASS")
print("PY_COMPILE=PASS")
print("REAL_RESULT_PRIORITY_PROBE=PASS")
print("BRIDGE_RESTART=PASS")
print("HEALTH_200=PASS")
print("HEAD=" + head)
