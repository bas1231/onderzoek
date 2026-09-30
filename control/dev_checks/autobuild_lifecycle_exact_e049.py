from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path.cwd()
PROD = Path.home() / "prediction_research_prod"
PY = str(PROD / ".venv/bin/python")
TARGETS = [
    "tests/codex_supervisor/test_candidate_dispatch.py",
    "tests/codex_supervisor/test_sol_builder_route.py",
]


def sync_local_snapshot() -> None:
    for path in PROD.rglob("*.py"):
        try:
            rel = path.relative_to(PROD)
        except ValueError:
            continue
        if any(part in {".git", ".venv", "__pycache__"} for part in rel.parts):
            continue
        if "tests" in rel.parts and rel.as_posix() not in TARGETS:
            continue
        if rel.parts[:2] == ("control", "dev_checks"):
            continue
        dst = ROOT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dst)


def main() -> None:
    sync_local_snapshot()
    runtime = ROOT / "control/dev_checks/pytest_e049"
    tmp_root = runtime / "tmp"
    base_temp = runtime / "basetemp"
    log_path = runtime / "pytest.log"
    tmp_root.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.pop("PYTEST_ADDOPTS", None)
    for key in ("TMPDIR", "TMP", "TEMP"):
        env[key] = str(tmp_root)
    cp = subprocess.run(
        [PY, "-m", "pytest", "-vv", "--tb=short", f"--basetemp={base_temp}", f"--log-file={log_path}", *TARGETS],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    out = cp.stdout or ""
    if cp.returncode == 0:
        print("E049_LIFECYCLE_TESTS_PASS")
        return
    lines = [line.strip() for line in out.splitlines() if line.strip()]
    keep = []
    for line in lines:
        if (
            line.startswith("E ")
            or line.startswith("FAILED ")
            or "AssertionError" in line
            or "assert " in line
            or "Blocked:" in line
            or "ValueError:" in line
        ):
            keep.append(line)
    payload = keep[-60:] if keep else lines[-100:]
    raise SystemExit("E049_LIFECYCLE_FAIL=" + " | ".join(payload)[:9000])


if __name__ == "__main__":
    main()
