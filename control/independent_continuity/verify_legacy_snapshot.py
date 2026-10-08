"""Read-only full pinned-source ledger acceptance check.

Must pass before installing the new standalone observer implementation.
Never writes proposals or edits the historical build log.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

try:
    from control.independent_continuity.observer import scan, load_events
except ModuleNotFoundError:
    from observer import scan, load_events


LEGACY_IDS = (
    "20261005T2045Z-A2Z-RESUME-E045",
    "20261005T2057Z-A2Z-COORDINATION-PROPOSAL",
)


def main() -> int:
    folder = Path("control/build_log/events")
    events, errors = load_events(folder)
    if errors:
        print("SNAPSHOT_INVALID=" + str(len(errors)) + " " + errors[0][:200])
        return 2
    by_id = {r["event_id"]: r for r in events}
    if len(by_id) != len(events):
        print("SNAPSHOT_INVALID=duplicate_event_id")
        return 2
    for ident in LEGACY_IDS:
        row = by_id.get(ident)
        if row is None or row.get("_opaque_event_type") is not True:
            print("SNAPSHOT_INVALID=legacy_guard_missing " + ident)
            return 2
    report = scan(folder, None, datetime.now(timezone.utc), 90)
    if report["status"] != "PASS" or report["can_auto_execute"] is not False:
        print("SNAPSHOT_INVALID=scan_rejected")
        return 2
    if any(rec.get("execution_authorized") is not False or
           rec.get("automatic_resubmission") is not False
           for rec in report["observations"]):
        print("SNAPSHOT_INVALID=prohibited_authority")
        return 2
    print(json.dumps({
        "snapshot": "PASS", "events_checked": len(events),
        "opaque_legacy_count": report["opaque_event_count"],
        "investigation_proposals": len(report["observations"]),
        "automatic_execution": False,
        "historical_files_changed": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
