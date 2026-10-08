"""Read-only diagnosis of deployed Reddit hook and canonical runtime preflight.

Do not fetch, run the hourly service, change branches, read credentials, or
alter any runtime state. Surface only the fail-closed sync reason.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def read_json(path: Path) -> dict:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except (OSError, UnicodeError, ValueError):
        return {}


def inspect(home: Path) -> dict:
    root = home / "prediction_research_prod"
    sync_path = home / ".local/state/prediction-research/prod-runtime-sync-latest.json"
    sync = read_json(sync_path)
    head = root / ".git/HEAD"
    try:
        ref = head.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        ref = "UNKNOWN"
    files = (
        "control/hourly/hourly_cycle.py",
        "control/reddit_idea_mine/arctic_shift_source.py",
        "control/reddit_idea_mine/hourly_ingress.py",
        "control/reddit_idea_mine/source_canary.py",
    )
    flags = [int((root / p).is_file()) for p in files]
    hourly = root / files[0]
    try:
        hook = "PREDICTION_REDDIT_ARCTIC_SHIFT_ENABLED" in hourly.read_text(
            encoding="utf-8", errors="replace"
        )
    except OSError:
        hook = False
    report = {
        "branch_ref": ref[:90],
        "sync": str(sync.get("status") or "NO_RECORD"),
        "sync_error": str(sync.get("error") or "")[:160],
        "sync_error_type": str(sync.get("error_type") or "")[:50],
        "sync_timestamp": str(sync.get("timestamp_utc") or "NO_RECORD")[:36],
        "modules_4": "".join(map(str, flags)),
        "hook": int(hook),
    }
    return report


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--check", required=True, action="store_true")
    p.parse_args()
    report = inspect(Path.home())
    print("REDDIT_RUNTIME_DIAG " + json.dumps(report, separators=(",", ":")))
    # Failing closed on absent installed source ensures compact bridge errors
    # display the diagnostic data, rather than a misleading task-level PASS.
    return 0 if report["modules_4"] == "1111" and report["hook"] == 1 else 12


if __name__ == "__main__":
    raise SystemExit(main())
