from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path.cwd()
PY = "/home/leonh/prediction_research_prod/.venv/bin/python"
TARGET = "tests/bridge/test_external_autobuild_continuation.py"


def main() -> None:
    env = os.environ.copy()
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env.pop("PYTEST_ADDOPTS", None)
    cp = subprocess.run(
        [PY, "-m", "pytest", "-q", "--tb=long", "--maxfail=1", TARGET],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=180,
        check=False,
    )
    lines = [line.strip() for line in (cp.stdout or "").splitlines() if line.strip()]
    internal = [line.split("INTERNALERROR>", 1)[-1].strip() for line in lines if "INTERNALERROR>" in line]
    permission = [line for line in lines if "PermissionError" in line or "project task guard" in line]
    last = internal[-1] if internal else (lines[-1] if lines else "NO_OUTPUT")
    perms = " || ".join(permission[-3:]) if permission else "NONE"
    print(f"PYTEST_ROOTCAUSE_RC={cp.returncode}|LAST={last[:900]}|PERMISSION={perms[:1200]}", flush=True)
    raise SystemExit(42)


if __name__ == "__main__":
    main()
