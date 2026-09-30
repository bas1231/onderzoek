from __future__ import annotations

import importlib.util
import os
import subprocess
from pathlib import Path

ROOT = Path.cwd()
E031 = ROOT / "control/dev_checks/autobuild_build_e031_runner.py"
PROD = Path.home() / "prediction_research_prod"
PY = str(PROD / ".venv/bin/python")


def load_e031():
    spec = importlib.util.spec_from_file_location("e031", E031)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def guarded_pytest(label: str, paths: list[str]) -> str:
    runtime = ROOT / "control/dev_checks/pytest_e034"
    tmp_root = runtime / "tmp"
    base_temp = runtime / ("basetemp_" + label.lower())
    log_path = runtime / (label.lower() + ".log")
    tmp_root.mkdir(parents=True, exist_ok=True)
    runtime.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env.pop("PYTEST_ADDOPTS", None)
    for key in ("TMPDIR", "TMP", "TEMP"):
        env[key] = str(tmp_root)

    args = [
        PY, "-m", "pytest", "-q",
        "--tb=line",
        f"--basetemp={base_temp}",
        f"--log-file={log_path}",
        *paths,
    ]
    cp = subprocess.run(
        args, cwd=ROOT, env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    out = cp.stdout or ""
    if cp.returncode != 0:
        lines = [line.strip() for line in out.splitlines() if line.strip()]
        important = [
            line for line in lines
            if line.startswith("E ")
            or "PermissionError" in line
            or "Blocked:" in line
            or "SOURCE_CHANGED" in line
            or line.startswith("FAILED ")
            or "AssertionError" in line
        ]
        payload = important[-16:] if important else lines[-32:]
        raise SystemExit("TEST_FAIL_" + label + "=" + " | ".join(payload)[:3800])
    lines = [line.strip() for line in out.splitlines() if line.strip()]
    return " | ".join(lines[-5:])[:900]


def main() -> None:
    m = load_e031()
    base = m.load_base()
    base.run_pytest = guarded_pytest
    m.load_base = lambda: base
    m.main()


if __name__ == "__main__":
    main()
