"""Bounded local intake of externally supplied discussion batches.

This module never requests Reddit or archives itself. Only explicit JSON files
placed in the permitted inbox are read, with no automatic candidate promotion.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from control.reddit_idea_mine.pipeline import run


def process(inbox: Path, root: Path, limit: int = 20) -> dict:
    if not inbox.is_dir() or not root.is_dir():
        raise ValueError("inbox and root must be existing directories")
    if inbox.is_symlink() or root.is_symlink():
        raise ValueError("symlink directory refused")
    if not isinstance(limit, int) or not 1 <= limit <= 20:
        raise ValueError("limit must be 1..20")
    rows = []
    for path in sorted(inbox.glob("*.json"))[:limit]:
        if path.is_symlink() or not path.is_file():
            rows.append({"file": path.name, "status": "REFUSED"})
            continue
        run_id = "reddit-inbox-" + path.stem
        try:
            result = run(path, root, run_id)
            rows.append({"file": path.name, "status": "PROCESSED", "recon_findings": result["recon_findings"]})
        except FileExistsError:
            rows.append({"file": path.name, "status": "ALREADY_PROCESSED"})
        except (ValueError, TypeError, OSError, json.JSONDecodeError) as exc:
            rows.append({"file": path.name, "status": "REJECTED", "reason": type(exc).__name__})
    return {"schema": "PREDICTION_REDDIT_INBOX_SWEEP_V1", "files_checked": len(rows),
            "results": rows, "live_trading": False, "paid_actions": False,
            "wallet_actions": False, "economic_conclusion": "NO_PROVEN_EDGE"}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--inbox", required=True, type=Path)
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--limit", type=int, default=20)
    a = p.parse_args()
    print(json.dumps(process(a.inbox, a.root, a.limit), sort_keys=True))


if __name__ == "__main__":
    main()
