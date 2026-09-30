from __future__ import annotations

import importlib.util
import os
import subprocess
from pathlib import Path

ROOT = Path.cwd()
BASE = ROOT / "control/dev_checks/autobuild_build_e031_runner.py"
PROD = Path.home() / "prediction_research_prod"
PY = str(PROD / ".venv/bin/python")


def load():
    spec = importlib.util.spec_from_file_location("e031", BASE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    m = load()
    base = m.load_base()
    base.prepare()
    pinned = m.sync_pins(base)
    env = os.environ.copy()
    env.pop("PYTEST_ADDOPTS", None)
    cp = subprocess.run(
        [PY, "-m", "pytest", "-q", "--tb=line", "tests/codex_supervisor/test_autobuild_runtime_wiring_e004i.py"],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    out = cp.stdout or ""
    if cp.returncode == 0:
        print("WIRING_EXACT=PASS pins=" + repr(sorted(pinned)))
        return
    lines = [line.strip() for line in out.splitlines() if line.strip()]
    interesting = [line for line in lines if "SUPERVISOR_SOURCE_CHANGED" in line or "SOURCE_CHANGED" in line or line.startswith("E ")]
    payload = interesting[-8:] if interesting else lines[-12:]
    raise SystemExit("WIRING_EXACT_FAIL=" + " | ".join(payload)[:3500])


if __name__ == "__main__":
    main()
