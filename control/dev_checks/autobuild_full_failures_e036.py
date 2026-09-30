from __future__ import annotations

import importlib.util
import os
import subprocess
from pathlib import Path

ROOT = Path.cwd()
E031 = ROOT / "control/dev_checks/autobuild_build_e031_runner.py"
PROD = Path.home() / "prediction_research_prod"
PY = str(PROD / ".venv/bin/python")
PATHS = [
    "tests/hourly/test_git_ai_exchange_v14.py",
    "tests/hourly/test_git_checkpoint_v15.py",
]


def load_e031():
    spec = importlib.util.spec_from_file_location("e031", E031)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    m = load_e031()
    base = m.load_base()
    base.prepare()
    m.sync_pins(base)

    runtime = ROOT / "control/dev_checks/pytest_e036"
    tmp_root = runtime / "tmp"
    base_temp = runtime / "basetemp"
    log_path = runtime / "hourly.log"
    tmp_root.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env.pop("PYTEST_ADDOPTS", None)
    for key in ("TMPDIR", "TMP", "TEMP"):
        env[key] = str(tmp_root)

    cp = subprocess.run(
        [PY, "-m", "pytest", "-q", "--tb=short", f"--basetemp={base_temp}", f"--log-file={log_path}", *PATHS],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    out = cp.stdout or ""
    if cp.returncode == 0:
        print("HOURLY_FILES=PASS")
        return
    lines = [line.strip() for line in out.splitlines() if line.strip()]
    keep = [
        line for line in lines
        if line.startswith("E ")
        or line.startswith("FAILED ")
        or "AssertionError" in line
        or "PermissionError" in line
        or "RuntimeError" in line
        or "CalledProcessError" in line
        or "blocked" in line.casefold()
        or "conflict" in line.casefold()
    ]
    payload = keep[-40:] if keep else lines[-60:]
    raise SystemExit("HOURLY_FILES_FAIL=" + " | ".join(payload)[:7000])


if __name__ == "__main__":
    main()
