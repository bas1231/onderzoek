from __future__ import annotations

import importlib.util
import os
import subprocess
from pathlib import Path

ROOT = Path.cwd()
PROD = Path.home() / "prediction_research_prod"
PY = str(PROD / ".venv/bin/python")
E043 = ROOT / "control/dev_checks/autobuild_build_e043_runner.py"
NODES = [
    "tests/hourly/test_ai_bridge_outbox.py::test_stalled_ai_delivery_is_reoffered_after_timeout",
    "tests/hourly/test_ai_bridge_outbox.py::test_fresh_or_legacy_ai_ack_is_not_replayed",
    "tests/hourly/test_ai_bridge_outbox.py::test_response_or_receipt_suppresses_stalled_retry",
]


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    e043 = load(E043, "e043_for_e044")
    e043.sync_python_sources()

    runtime = ROOT / "control/dev_checks/pytest_e044"
    runtime.mkdir(parents=True, exist_ok=True)
    tmp_root = runtime / "tmp"
    tmp_root.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.pop("PYTEST_ADDOPTS", None)
    for key in ("TMPDIR", "TMP", "TEMP"):
        env[key] = str(tmp_root)

    cp = subprocess.run(
        [
            PY, "-m", "pytest", "-q", "--tb=short",
            f"--basetemp={runtime / 'basetemp'}",
            f"--log-file={runtime / 'outbox.log'}",
            *NODES,
        ],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    out = cp.stdout or ""
    if cp.returncode == 0:
        print("OUTBOX3=PASS")
        return
    lines = [line.strip() for line in out.splitlines() if line.strip()]
    keep = [
        line for line in lines
        if line.startswith("E ")
        or line.startswith("FAILED ")
        or "AssertionError" in line
        or "PermissionError" in line
        or "assert " in line
        or "AttributeError" in line
        or "TypeError" in line
    ]
    payload = keep[-40:] if keep else lines[-60:]
    raise SystemExit("OUTBOX3_FAIL=" + " | ".join(payload)[:7000])


if __name__ == "__main__":
    main()
