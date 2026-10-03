from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path.cwd()
PY = "/home/leonh/prediction_research_prod/.venv/bin/python"
TARGETS = [
    "tests/bridge/test_external_autobuild_continuation.py",
    "tests/bridge/test_continuation_wake_overlay.py",
    "tests/codex_supervisor/test_autobuild_chat_wake.py",
    "tests/codex_supervisor/test_candidate_dispatch.py",
    "tests/codex_supervisor/test_supervisor.py",
]


def main() -> None:
    env = os.environ.copy()
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env.pop("PYTEST_ADDOPTS", None)
    cp = subprocess.run(
        [PY, "-m", "pytest", "-q", *TARGETS],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=420,
        check=False,
    )
    out = cp.stdout or ""
    tail = " | ".join(line.strip() for line in out.splitlines()[-30:] if line.strip())[:3600]
    print(f"HERMETIC_PYTEST_RC={cp.returncode}|DETAIL={tail}", flush=True)
    if cp.returncode != 0:
        raise SystemExit(41)


if __name__ == "__main__":
    main()
