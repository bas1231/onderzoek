"""Read-only health assertion for the independent continuity service.

Use the existing project executor's guarded subprocess journalctl access.
A failing service is reported as an ordinary failed assertion.
"""
from __future__ import annotations

import json
import subprocess


def main() -> None:
    completed = subprocess.run(
        ["journalctl", "--user", "-u", "prediction-independent-continuity.service",
         "-n", "40", "-o", "cat", "--no-pager"],
        capture_output=True, text=True, check=True, timeout=30,
    )
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    failures = [
        line for line in lines
        if any(token in line.lower() for token in (
            "fail_closed", "traceback", "error:", "exception:", "failed at step",
            "failed to", "permission denied",
        ))
    ]
    if failures:
        raise AssertionError("Independent service journal failure: " + failures[-1][:350])
    print(json.dumps({"service": "prediction-independent-continuity.service",
                      "journal_lines": len(lines), "classification": "NO_FAILURE_LINE"}))


if __name__ == "__main__":
    main()
