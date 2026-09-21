from __future__ import annotations

import importlib.util
import json
import py_compile
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path.cwd()
SERVICE = "prediction-research-browser-bridge.service"
TARGET = ROOT / "control/browser_bridge.py"
TASK_ID = sys.argv[1] if len(sys.argv) > 1 else ""


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=check)


def tracked_clean() -> bool:
    return (
        run("git", "diff", "--quiet", check=False).returncode == 0
        and run("git", "diff", "--cached", "--quiet", check=False).returncode == 0
    )


def commit_if_staged(message: str) -> None:
    if run("git", "diff", "--cached", "--quiet", check=False).returncode != 0:
        run("git", "commit", "-m", message)


def checkpoint_executor_move() -> None:
    run("git", "add", "-u")
    if TASK_ID:
        running = ROOT / "control/tasks/running" / f"{TASK_ID}.json"
        if running.exists():
            run("git", "add", "--", running.relative_to(ROOT).as_posix())
    commit_if_staged("control: checkpoint executor state before E383 recovery")
    print("PRE_E383_CHECKPOINT=PASS")


def ensure_result_priority() -> None:
    text = TARGET.read_text(encoding="utf-8")
    if "REAL_RESULTS_BEFORE_INCIDENTS_E379" not in text:
        print("RESULT_PRIORITY_PATCH=FAIL:MISSING_E379_MARKER")
        raise SystemExit(51)
    py_compile.compile(str(TARGET), doraise=True)
    print("RESULT_PRIORITY_PATCH=PASS")


def ensure_ack_patch() -> None:
    text = TARGET.read_text(encoding="utf-8")
    old = '''def acknowledge(task_id: str) -> dict:\n    state = load_state()\n\n    if task_id not in state.get("bridge_tasks", []):\n        return {\n            "ok": False,\n            "error": "unknown bridge task",\n        }\n\n    acked = state.setdefault("acked", [])\n\n    if task_id not in acked:\n        acked.append(task_id)\n\n    save_state(state)\n\n    lifecycle_update(\n        task_id,\n        "ACKED",\n        "browser acknowledged result",\n    )\n\n    return {\n        "ok": True,\n        "task_id": task_id,\n    }\n'''
    new = '''def acknowledge(task_id: str) -> dict:\n    state = load_state()\n\n    if not TASK_ID_RE.fullmatch(task_id):\n        return {\n            "ok": False,\n            "error": "invalid task_id",\n        }\n\n    bridge_tasks = state.setdefault("bridge_tasks", [])\n    known = task_id in bridge_tasks\n    result_exists = (RESULTS / task_id / "RESULT.json").exists()\n    incident_item = task_id.startswith("INCIDENT-")\n\n    if not (known or result_exists or incident_item):\n        return {\n            "ok": False,\n            "error": "unknown bridge task",\n        }\n\n    if task_id not in bridge_tasks:\n        bridge_tasks.append(task_id)\n\n    acked = state.setdefault("acked", [])\n\n    if task_id not in acked:\n        acked.append(task_id)\n\n    save_state(state)\n\n    lifecycle_update(\n        task_id,\n        "ACKED",\n        "browser acknowledged result",\n    )\n\n    return {\n        "ok": True,\n        "task_id": task_id,\n        "recovered": not known,\n    }\n'''
    if old in text:
        TARGET.write_text(text.replace(old, new, 1), encoding="utf-8")
    elif '"recovered": not known' not in text:
        print("ACK_PATCH=FAIL:ANCHOR_MISSING")
        raise SystemExit(52)

    py_compile.compile(str(TARGET), doraise=True)
    print("ACK_PATCH_COMPILE=PASS")

    spec = importlib.util.spec_from_file_location("bridge_e383_probe", TARGET)
    if spec is None or spec.loader is None:
        raise SystemExit(53)
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
        probe_id = "INCIDENT-E383-ACK-PROBE"
        response = mod.acknowledge(probe_id)
        state = json.loads(mod.STATE_FILE.read_text(encoding="utf-8"))
        assert response.get("ok") is True, response
        assert probe_id in state.get("acked", []), state
        assert mod.acknowledge(probe_id).get("ok") is True
    print("INCIDENT_ACK_PROBE=PASS")

    run("git", "add", "--", "control/browser_bridge.py")
    commit_if_staged("fix: make bridge result ack durable")
    print("ACK_PATCH_COMMIT=PASS")


def sync_main() -> None:
    run("git", "fetch", "origin", "main")
    head = run("git", "rev-parse", "HEAD").stdout.strip()
    remote = run("git", "rev-parse", "origin/main").stdout.strip()
    div = run("git", "rev-list", "--left-right", "--count", "HEAD...origin/main").stdout.strip()
    print("PRE_HEAD=" + head)
    print("PRE_ORIGIN_MAIN=" + remote)
    print("PRE_DIVERGENCE=" + div)
    if not tracked_clean():
        print("TRACKED_CLEAN_BEFORE_SYNC=FAIL")
        print(run("git", "status", "--porcelain=v1").stdout.rstrip())
        raise SystemExit(54)
    print("TRACKED_CLEAN_BEFORE_SYNC=PASS")

    if head != remote:
        backup = f"recovery/e383-pre-sync-{head[:12]}"
        run("git", "branch", "-f", backup, head)
        print("BACKUP_BRANCH=" + backup)
        head_is_ancestor = run("git", "merge-base", "--is-ancestor", "HEAD", "origin/main", check=False).returncode == 0
        remote_is_ancestor = run("git", "merge-base", "--is-ancestor", "origin/main", "HEAD", check=False).returncode == 0
        if head_is_ancestor:
            run("git", "merge", "--ff-only", "origin/main")
            print("SYNC_MODE=FAST_FORWARD")
        elif remote_is_ancestor:
            print("SYNC_MODE=LOCAL_AHEAD")
        else:
            merged = run("git", "merge", "--no-edit", "origin/main", check=False)
            if merged.returncode != 0:
                print("SYNC_MODE=DIVERGED_CONFLICT")
                print(merged.stdout.strip())
                print(merged.stderr.strip())
                run("git", "merge", "--abort", check=False)
                raise SystemExit(55)
            print("SYNC_MODE=DIVERGED_MERGED")

    pushed = run("git", "push", "origin", "HEAD:main", check=False)
    if pushed.returncode != 0:
        print("PUSH_ATTEMPT_1=FAIL")
        run("git", "fetch", "origin", "main")
        merged = run("git", "merge", "--no-edit", "origin/main", check=False)
        if merged.returncode != 0:
            print(merged.stdout.strip())
            print(merged.stderr.strip())
            run("git", "merge", "--abort", check=False)
            raise SystemExit(56)
        pushed = run("git", "push", "origin", "HEAD:main", check=False)
        if pushed.returncode != 0:
            print(pushed.stdout.strip())
            print(pushed.stderr.strip())
            raise SystemExit(57)
    print("PUSH_MAIN=PASS")

    run("git", "fetch", "origin", "main")
    head = run("git", "rev-parse", "HEAD").stdout.strip()
    remote = run("git", "rev-parse", "origin/main").stdout.strip()
    div = run("git", "rev-list", "--left-right", "--count", "HEAD...origin/main").stdout.strip()
    print("FINAL_HEAD=" + head)
    print("FINAL_ORIGIN_MAIN=" + remote)
    print("FINAL_DIVERGENCE=" + div)
    if head != remote or div != "0\t0":
        raise SystemExit(58)
    print("LOCAL_REMOTE_SYNC=PASS")


def restart_and_wait() -> None:
    run("systemctl", "--user", "daemon-reload", check=False)
    restarted = run("systemctl", "--user", "restart", SERVICE, check=False)
    if restarted.returncode != 0:
        print("BRIDGE_RESTART_COMMAND=FAIL")
        print(restarted.stdout.strip())
        print(restarted.stderr.strip())
    else:
        print("BRIDGE_RESTART_COMMAND=PASS")

    last_error = ""
    for attempt in range(1, 31):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8765/health", timeout=2) as response:
                if response.status == 200:
                    print("HEALTH_200=PASS")
                    print("HEALTH_ATTEMPT=" + str(attempt))
                    print("BRIDGE_RESTART=PASS")
                    return
        except Exception as exc:
            last_error = repr(exc)
        time.sleep(0.5)

    print("HEALTH_200=FAIL")
    print("HEALTH_LAST_ERROR=" + last_error)
    status = run("systemctl", "--user", "status", SERVICE, "--no-pager", check=False)
    print("SYSTEMCTL_STATUS_BEGIN")
    print(status.stdout.rstrip())
    print(status.stderr.rstrip())
    print("SYSTEMCTL_STATUS_END")
    journal = run("journalctl", "--user", "-u", SERVICE, "-n", "100", "--no-pager", check=False)
    print("JOURNAL_BEGIN")
    print(journal.stdout.rstrip())
    print(journal.stderr.rstrip())
    print("JOURNAL_END")
    raise SystemExit(59)


branch = run("git", "branch", "--show-current").stdout.strip()
if branch != "main":
    print("BRANCH_CHECK=FAIL:" + branch)
    raise SystemExit(50)
print("BRANCH_CHECK=PASS")
checkpoint_executor_move()
ensure_result_priority()
ensure_ack_patch()
sync_main()
py_compile.compile(str(TARGET), doraise=True)
print("FINAL_COMPILE=PASS")
restart_and_wait()
print("CONTROL_PLANE_RECOVER_SYNC_E383=PASS")
