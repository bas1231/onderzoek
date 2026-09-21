from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path.cwd()


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=check)


def tracked_clean() -> bool:
    return (
        run("git", "diff", "--quiet", check=False).returncode == 0
        and run("git", "diff", "--cached", "--quiet", check=False).returncode == 0
    )


def sync_once() -> None:
    run("git", "fetch", "origin", "main")
    head = run("git", "rev-parse", "HEAD").stdout.strip()
    remote = run("git", "rev-parse", "origin/main").stdout.strip()
    if head == remote:
        return

    backup = f"recovery/e382-pre-sync-{head[:12]}"
    run("git", "branch", "-f", backup, head)
    print("BACKUP_BRANCH=" + backup)

    head_is_ancestor = run(
        "git", "merge-base", "--is-ancestor", "HEAD", "origin/main", check=False
    ).returncode == 0
    remote_is_ancestor = run(
        "git", "merge-base", "--is-ancestor", "origin/main", "HEAD", check=False
    ).returncode == 0

    if head_is_ancestor:
        run("git", "merge", "--ff-only", "origin/main")
        print("SYNC_MODE=FAST_FORWARD")
    elif remote_is_ancestor:
        print("SYNC_MODE=LOCAL_AHEAD")
    else:
        merged = run("git", "merge", "--no-edit", "origin/main", check=False)
        if merged.returncode != 0:
            run("git", "merge", "--abort", check=False)
            print("SYNC_MODE=DIVERGED_CONFLICT")
            print(merged.stdout.strip())
            print(merged.stderr.strip())
            raise SystemExit(41)
        print("SYNC_MODE=DIVERGED_MERGED")

    pushed = run("git", "push", "origin", "HEAD:main", check=False)
    if pushed.returncode != 0:
        print("PUSH_ATTEMPT_1=FAIL")
        run("git", "fetch", "origin", "main")
        merged = run("git", "merge", "--no-edit", "origin/main", check=False)
        if merged.returncode != 0:
            run("git", "merge", "--abort", check=False)
            print(merged.stdout.strip())
            print(merged.stderr.strip())
            raise SystemExit(42)
        pushed = run("git", "push", "origin", "HEAD:main", check=False)
        if pushed.returncode != 0:
            print(pushed.stdout.strip())
            print(pushed.stderr.strip())
            raise SystemExit(43)
    print("PUSH_MAIN=PASS")


branch = run("git", "branch", "--show-current").stdout.strip()
if branch != "main":
    print("BRANCH_CHECK=FAIL:" + branch)
    raise SystemExit(30)
print("BRANCH_CHECK=PASS")

run("git", "fetch", "origin", "main")
pre_head = run("git", "rev-parse", "HEAD").stdout.strip()
pre_remote = run("git", "rev-parse", "origin/main").stdout.strip()
pre_div = run("git", "rev-list", "--left-right", "--count", "HEAD...origin/main").stdout.strip()
print("PRE_HEAD=" + pre_head)
print("PRE_ORIGIN_MAIN=" + pre_remote)
print("PRE_DIVERGENCE=" + pre_div)

if not tracked_clean():
    print("TRACKED_CLEAN_BEFORE=FAIL")
    print(run("git", "status", "--porcelain=v1").stdout.rstrip())
    raise SystemExit(31)
print("TRACKED_CLEAN_BEFORE=PASS")

repair_bytes = subprocess.run(
    ["git", "show", "origin/main:control/jobs/repair_bridge_delivery_e381.py"],
    cwd=ROOT,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    check=True,
).stdout
with tempfile.TemporaryDirectory() as td:
    repair = pathlib.Path(td) / "repair_bridge_delivery_e381.py"
    repair.write_bytes(repair_bytes)
    rc = subprocess.run([sys.executable, str(repair)], cwd=ROOT).returncode
    if rc != 0:
        print(f"E381_REPAIR=FAIL:{rc}")
        raise SystemExit(rc)
print("E381_REPAIR=PASS")

if not tracked_clean():
    print("TRACKED_CLEAN_AFTER_REPAIR=FAIL")
    print(run("git", "status", "--porcelain=v1").stdout.rstrip())
    raise SystemExit(32)
print("TRACKED_CLEAN_AFTER_REPAIR=PASS")

sync_once()
run("git", "fetch", "origin", "main")
head = run("git", "rev-parse", "HEAD").stdout.strip()
remote = run("git", "rev-parse", "origin/main").stdout.strip()
div = run("git", "rev-list", "--left-right", "--count", "HEAD...origin/main").stdout.strip()
print("FINAL_HEAD=" + head)
print("FINAL_ORIGIN_MAIN=" + remote)
print("FINAL_DIVERGENCE=" + div)
if head != remote or div != "0\t0":
    raise SystemExit(44)
print("LOCAL_REMOTE_SYNC=PASS")

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
print("CONTROL_PLANE_RECOVER_SYNC_E382=PASS")
