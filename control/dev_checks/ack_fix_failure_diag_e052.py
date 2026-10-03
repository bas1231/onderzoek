from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys

ROOT = Path.cwd()
TARGETS = [
    "tests/audit/test_delivery_behavior.py",
    "tests/audit/test_reliability_regressions.py",
    "tests/bridge/test_tampermonkey_multichat.py",
    "control/tampermonkey_multichat/test_userscript_delivery_dedupe_static.py",
    "control/tampermonkey_multichat/test_userscript_v046_guard_static.py",
]

def main() -> int:
    env = os.environ.copy()
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    cp = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *TARGETS],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=420,
    )
    out = cp.stdout or ""
    failed = []
    errors = []
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("FAILED "):
            failed.append(s.split(" - ", 1)[0])
        elif s.startswith("ERROR "):
            errors.append(s.split(" - ", 1)[0])
    if cp.returncode == 0:
        print("ACK_FIX_DIAG=PASS")
        return 0
    detail = "|".join((failed + errors)[-16:]) or "NO_FAIL_LINES"
    print("ACK_FIX_DIAG=FAIL|" + detail, flush=True)
    return 42

if __name__ == "__main__":
    raise SystemExit(main())
