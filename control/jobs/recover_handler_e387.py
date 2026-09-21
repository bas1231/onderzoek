from __future__ import annotations

import os
import pathlib
import py_compile
import subprocess
import sys
import time
import urllib.request

ROOT = pathlib.Path.cwd()
TARGET = ROOT / "control/browser_bridge.py"
GOOD_REF = "8cdc407a7242a27dad7017ae03e15de18f3bb607"
SERVICE = "prediction-research-browser-bridge.service"


def run(*args: str, check: bool = True, env=None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=check, env=env)


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run("git", *args, check=check)


branch = git("branch", "--show-current").stdout.strip()
if branch != "main":
    print("BRANCH_CHECK=FAIL:" + branch)
    raise SystemExit(70)
print("BRANCH_CHECK=PASS")

current = TARGET.read_text(encoding="utf-8")
if "class Handler(BaseHTTPRequestHandler):" not in current:
    good = git("show", f"{GOOD_REF}:control/browser_bridge.py").stdout
    h0 = good.find("class Handler(BaseHTTPRequestHandler):")
    h1 = good.find("\ndef main():", h0)
    if h0 < 0 or h1 < 0:
        print("HANDLER_SOURCE=FAIL")
        raise SystemExit(71)
    handler_block = good[h0:h1].rstrip() + "\n\n\n"
    main_pos = current.find("def main():")
    if main_pos < 0:
        print("MAIN_ANCHOR=FAIL")
        raise SystemExit(72)
    backup = TARGET.with_suffix(".py.e387.bak")
    backup.write_text(current, encoding="utf-8")
    TARGET.write_text(current[:main_pos] + handler_block + current[main_pos:], encoding="utf-8")
    print("HANDLER_RESTORE=PASS")
    print("LOCAL_BACKUP=" + str(backup))
else:
    print("HANDLER_RESTORE=ALREADY_PRESENT")

py_compile.compile(str(TARGET), doraise=True)
print("PY_COMPILE=PASS")

env = os.environ.copy()
control_path = str(ROOT / "control")
existing = env.get("PYTHONPATH", "")
env["PYTHONPATH"] = control_path if not existing else control_path + os.pathsep + existing
probe = run(sys.executable, "-c", "import importlib.util,pathlib,sys; p=pathlib.Path('control/browser_bridge.py'); s=importlib.util.spec_from_file_location('bridge_e387_probe',p); m=importlib.util.module_from_spec(s); sys.modules[s.name]=m; s.loader.exec_module(m); assert hasattr(m,'Handler'); print('HANDLER_IMPORT_PROBE=PASS')", env=env)
print(probe.stdout.strip())

if git("diff", "--quiet", check=False).returncode != 0:
    git("add", "--", "control/browser_bridge.py")
    git("commit", "-m", "fix: restore bridge Handler after ACK recovery")
    print("HANDLER_COMMIT=PASS")
else:
    print("HANDLER_COMMIT=NO_CHANGE")

git("fetch", "origin", "main")
merge = git("merge", "--no-edit", "origin/main", check=False)
if merge.returncode != 0:
    print("MERGE_ORIGIN_MAIN=FAIL")
    print(merge.stdout.strip())
    print(merge.stderr.strip())
    git("merge", "--abort", check=False)
    raise SystemExit(73)
print("MERGE_ORIGIN_MAIN=PASS")

push = git("push", "origin", "HEAD:main", check=False)
if push.returncode != 0:
    print("PUSH_MAIN=FAIL")
    print(push.stdout.strip())
    print(push.stderr.strip())
    raise SystemExit(74)
print("PUSH_MAIN=PASS")

git("fetch", "origin", "main")
head = git("rev-parse", "HEAD").stdout.strip()
remote = git("rev-parse", "origin/main").stdout.strip()
div = git("rev-list", "--left-right", "--count", "HEAD...origin/main").stdout.strip()
print("FINAL_HEAD=" + head)
print("FINAL_ORIGIN_MAIN=" + remote)
print("FINAL_DIVERGENCE=" + div)
if head != remote or div != "0\t0":
    raise SystemExit(75)
print("LOCAL_REMOTE_SYNC=PASS")

run("systemctl", "--user", "daemon-reload", check=False)
restart = run("systemctl", "--user", "restart", SERVICE, check=False)
if restart.returncode != 0:
    print("BRIDGE_RESTART_COMMAND=FAIL")
    print(restart.stdout.strip())
    print(restart.stderr.strip())
    raise SystemExit(76)
print("BRIDGE_RESTART_COMMAND=PASS")

last_error = ""
for attempt in range(1, 31):
    try:
        with urllib.request.urlopen("http://127.0.0.1:8765/health", timeout=2) as response:
            if response.status == 200:
                print("HEALTH_200=PASS")
                print("HEALTH_ATTEMPT=" + str(attempt))
                print("CONTROL_PLANE_RECOVER_HANDLER_E387=PASS")
                raise SystemExit(0)
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
raise SystemExit(77)
