"""Read-only proof gate for installed hourly Arctic Shift -> Recon observations.

This never issues network requests, changes runtime files, reads credentials,
starts services, or authorizes candidate promotion. It checks receipt provenance
and report persistence from actual previously executed hourly cycles.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def read_object(path: Path) -> dict:
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
        return result if isinstance(result, dict) else {}
    except (OSError, ValueError, UnicodeError):
        return {}


def probe(root: Path, state: Path) -> dict:
    hourly = root / "control/hourly/hourly_cycle.py"
    ingest = root / "control/reddit_idea_mine/hourly_ingress.py"
    source = root / "control/reddit_idea_mine/arctic_shift_source.py"
    canary = root / "control/reddit_idea_mine/source_canary.py"
    installed = all(p.is_file() for p in (hourly, ingest, source, canary))
    hook = installed and "PREDICTION_REDDIT_ARCTIC_SHIFT_ENABLED" in (
        hourly.read_text(encoding="utf-8", errors="replace")
    )
    sync = read_object(state)
    receipts_path = root / "knowledge/runs/reddit_idea_mine"
    try:
        receipt_paths = sorted(
            receipts_path.glob("*-hourly-source.json"),
            key=lambda p: p.stat().st_mtime, reverse=True,
        )[:50] if receipts_path.is_dir() else []
    except OSError:
        receipt_paths = []

    enabled_count = 0
    real_data_count = 0
    reported_count = 0
    states = {}
    sample = {}
    for path in receipt_paths:
        obj = read_object(path)
        status = str(obj.get("status") or "INVALID")
        states[status] = states.get(status, 0) + 1
        if obj.get("enabled") is True:
            enabled_count += 1
        populated = (
            obj.get("enabled") is True
            and obj.get("provider") == "arctic_shift"
            and status in {"SUCCESS", "PARTIAL"}
            and isinstance(obj.get("posts_received"), int)
            and obj["posts_received"] > 0
            and isinstance(obj.get("leads_accepted"), int)
            and obj["leads_accepted"] > 0
            and isinstance(obj.get("evidence_added"), int)
            and obj["evidence_added"] > 0
            and obj.get("economic_conclusion") == "NO_PROVEN_EDGE"
        )
        if not populated:
            continue
        real_data_count += 1
        run_id = path.name[:-len("-hourly-source.json")]
        manifest_path = root / "knowledge/runs" / (run_id + ".json")
        report_path = root / "hourly-reports" / (run_id + ".md")
        manifest = read_object(manifest_path)
        section = ""
        if report_path.is_file():
            try:
                section = report_path.read_text(
                    encoding="utf-8", errors="replace"
                )
            except OSError:
                pass
        x = manifest.get("reddit_idea_mine") or {}
        if (isinstance(x, dict)
            and x.get("receipt_ref")
                == "knowledge/runs/reddit_idea_mine/" + path.name
            and x.get("evidence_added", 0) > 0
            and "### Reddit Idea Mine source" in section):
            reported_count += 1
            sample = {
                "posts_received": obj["posts_received"],
                "leads_accepted": obj["leads_accepted"],
                "evidence_added": obj["evidence_added"],
                "run_id": run_id[:100],
            }

    proven = bool(hook and reported_count)
    return {
        "schema": "PREDICTION_REDDIT_INSTALLED_OPERATIONAL_CHECK_V1",
        "status": "OPERATIONAL_PROVEN" if proven else "NOT_YET_PROVEN",
        "installed_modules": installed,
        "hourly_hook_present": hook,
        "runtime_sync_last_status": sync.get("status", "NOT_OBSERVED"),
        "last_receipts_checked": len(receipt_paths),
        "receipt_status_counts": states,
        "enabled_receipts": enabled_count,
        "populated_recon_receipts": real_data_count,
        "canonical_report_matches": reported_count,
        "sample": sample,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "economic_conclusion": "NO_PROVEN_EDGE",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", required=True)
    args = parser.parse_args()
    if not args.check:
        return 2
    home = Path.home()
    report = probe(
        home / "prediction_research_prod",
        home / ".local/state/prediction-research/prod-runtime-sync-latest.json",
    )
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "OPERATIONAL_PROVEN" else 12


if __name__ == "__main__":
    raise SystemExit(main())
