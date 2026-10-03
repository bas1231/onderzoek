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


def compact_internal_error(output: str) -> str:
    lines = [line.rstrip() for line in output.splitlines()]
    internal = [line for line in lines if "INTERNALERROR>" in line]
    if internal:
        cleaned = []
        for line in internal:
            part = line.split("INTERNALERROR>", 1)[-1].strip()
            if part:
                cleaned.append(part)
        payload = " | ".join(cleaned[-40:])
    else:
        interesting = [
            line.strip()
            for line in lines
            if (
                "Traceback" in line
                or line.lstrip().startswith("File ")
                or line.startswith("E ")
                or "Error" in line
                or "Exception" in line
                or "Permission" in line
                or "blocked" in line.lower()
                or "denied" in line.lower()
            )
        ]
        payload = " | ".join(interesting[-40:] if interesting else [x.strip() for x in lines[-50:] if x.strip()])
    return " ".join(payload.split())[:3600]


def main() -> None:
    env = os.environ.copy()
    env.pop("PYTEST_ADDOPTS", None)
    cmd = [
        PY,
        "-m",
        "pytest",
        "-vv",
        "--tb=long",
        "--maxfail=1",
        *TARGETS,
    ]
    cp = subprocess.run(
        cmd,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=300,
        check=False,
    )
    summary = compact_internal_error(cp.stdout or "")
    print(f"PYTEST_DIAG_RC={cp.returncode}|DETAIL={summary}", flush=True)
    raise SystemExit(42)


if __name__ == "__main__":
    main()
