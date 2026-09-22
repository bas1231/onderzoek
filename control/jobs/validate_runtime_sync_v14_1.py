from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / ".venv/bin/python"


def run(command: list[str]) -> dict[str, object]:
    proc = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=240,
    )
    return {
        "command": command,
        "returncode": proc.returncode,
        "output": proc.stdout[-12000:],
    }


def main() -> int:
    python = str(PYTHON if PYTHON.exists() else Path(sys.executable))
    checks = [
        run([
            python,
            "-m",
            "pytest",
            "tests/hourly/test_runtime_sync_state_aware_v14.py",
            "-q",
        ]),
        run([
            python,
            "-m",
            "compileall",
            "-q",
            "control/hourly/runtime_sync.py",
            "control/hourly/install_runtime_sync.py",
            "control/jobs/validate_runtime_sync_v14_1.py",
        ]),
        run([
            python,
            "control/hourly/install_runtime_sync.py",
            "--dry-run",
        ]),
    ]
    ok = all(check["returncode"] == 0 for check in checks)
    result = {
        "schema": "PVA_RUNTIME_SYNC_VALIDATION_V1",
        "ok": ok,
        "checks": checks,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
