from __future__ import annotations

import hashlib
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path.cwd()
TASK_ID = sys.argv[1] if len(sys.argv) > 1 else ""


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        args,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


branch = run("git", "branch", "--show-current").stdout.decode().strip()
if branch != "main":
    print("BRANCH_CHECK=FAIL:" + branch)
    raise SystemExit(70)
print("BRANCH_CHECK=PASS")

run("git", "fetch", "origin", "main")

raw = run("git", "ls-files", "--others", "--exclude-standard", "-z").stdout
untracked = [p.decode() for p in raw.split(b"\0") if p]
conflicts: list[str] = []
for rel in untracked:
    probe = run("git", "cat-file", "-e", f"origin/main:{rel}", check=False)
    if probe.returncode == 0:
        conflicts.append(rel)

print("UNTRACKED_TOTAL=" + str(len(untracked)))
print("UNTRACKED_REMOTE_CONFLICTS=" + str(len(conflicts)))

stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
backup_root = pathlib.Path.home() / ".local" / "state" / "prediction-research" / "recovery" / ("e386-" + stamp)

for rel in conflicts:
    src = ROOT / rel
    if not src.is_file():
        print("UNTRACKED_CONFLICT_UNSAFE=" + rel)
        raise SystemExit(71)
    local_bytes = src.read_bytes()
    remote_bytes = run("git", "show", f"origin/main:{rel}").stdout
    dst = backup_root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    if dst.read_bytes() != local_bytes:
        print("BACKUP_VERIFY=FAIL:" + rel)
        raise SystemExit(72)
    relation = "IDENTICAL" if local_bytes == remote_bytes else "DIFFERENT"
    print("QUARANTINE=" + rel + ":" + relation + ":local=" + sha256(local_bytes) + ":remote=" + sha256(remote_bytes))
    src.unlink()

if conflicts:
    print("UNTRACKED_CONFLICT_BACKUP=" + str(backup_root))
print("UNTRACKED_CONFLICT_QUARANTINE=PASS")

script_bytes = run("git", "show", "origin/main:control/jobs/recover_bridge_e385.py").stdout
env = os.environ.copy()
control_path = str(ROOT / "control")
existing = env.get("PYTHONPATH", "")
env["PYTHONPATH"] = control_path if not existing else control_path + os.pathsep + existing

with tempfile.TemporaryDirectory() as td:
    script = pathlib.Path(td) / "recover_bridge_e385.py"
    script.write_bytes(script_bytes)
    rc = subprocess.run([sys.executable, str(script), TASK_ID], cwd=ROOT, env=env).returncode
    if rc != 0:
        print(f"E385_CHAIN=FAIL:{rc}")
        raise SystemExit(rc)

print("E385_CHAIN=PASS")
print("CONTROL_PLANE_RECOVER_SYNC_E386=PASS")
