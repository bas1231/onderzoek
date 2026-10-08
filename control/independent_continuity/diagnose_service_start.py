"""Read-only diagnostic for the standalone Prediction continuity observer.

Checks the observer's own systemd journal, returns a brief classified startup
failure. Never changes a unit, its environment, the bridge or executor.
"""
from __future__ import annotations

import json
import re
import subprocess


UNIT = "prediction-independent-continuity.service"
FLAGS = ("traceback", "error:", "exception:", "failed", "permission denied")


def describe_journal(log: str) -> tuple[str, str]:
    rows = [line.strip() for line in log.splitlines() if line.strip()]
    for line in reversed(rows):
        try:
            obj = json.loads(line)
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(obj, dict) and obj.get("status") == "FAIL_CLOSED":
            return "OBSERVER_FAIL_CLOSED", str(obj.get("reason") or "reason missing")[:250]
        if isinstance(obj, dict) and obj.get("status") == "INPUT_INVALID":
            failures = obj.get("errors") or []
            return "OBSERVER_INPUT_INVALID", str(failures[0] if failures else "input invalid")[:250]
    for line in reversed(rows):
        if any(flag in line.lower() for flag in FLAGS):
            return "OBSERVER_JOURNAL_ERROR", line[-250:]
    return "OBSERVER_CAUSE_UNCLASSIFIED", "No observer error line found in latest 70 journal records"


def main() -> int:
    try:
        result = subprocess.run(
            ["journalctl", "--user", "-u", UNIT, "-n", "70",
             "--no-pager", "-o", "cat"],
            capture_output=True, text=True, timeout=25, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        print("OBSERVER_DIAG=JOURNAL_UNAVAILABLE")
        return 2
    if result.returncode != 0:
        print("OBSERVER_DIAG=JOURNAL_ACCESS_FAILED")
        return 2
    code, detail = describe_journal(result.stdout[-16000:])
    # Report a single bounded finding, with no unrelated journal content.
    safe = re.sub(r"[^a-zA-Z0-9 _.:/()=+,-]", " ", detail)
    print(f"OBSERVER_DIAG={code} {safe[:230]}", flush=True)
    return 2  # Diagnosis alone never proves this failed service is healthy.


if __name__ == "__main__":
    raise SystemExit(main())
