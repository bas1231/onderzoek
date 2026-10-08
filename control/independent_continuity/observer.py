"""Independent, read-only Prediction continuity observer.

No imports from the bridge or project executor; no network, shell, orders,
GitHub writes, browser injection, task submission or service management.
Emits immutable *diagnostic* proposals, never execution authority.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time

SUBSTANTIVE = {"PLAN", "ATTEMPT", "RESULT", "DECISION", "HANDOFF", "CLOSE"}
FINAL = {"DONE", "BLOCKED"}
MAX_BYTES = 1024 * 1024


def utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("missing UTC timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("naive timestamp forbidden")
    return parsed.astimezone(timezone.utc)


def load_events(folder: Path) -> tuple[list[dict], list[str]]:
    if not folder.is_dir():
        raise ValueError("events directory missing")
    records: list[dict] = []
    errors: list[str] = []
    for path in sorted(folder.glob("*.json")):
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
                raise ValueError("unsafe or oversized event file")
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict) or value.get("schema") != "PREDICTION_BUILD_LOG_EVENT_V1":
                raise ValueError("unknown build-log schema")
            if not isinstance(value.get("work_item_id"), str) or not value["work_item_id"]:
                raise ValueError("missing work item identity")
            if not isinstance(value.get("event_id"), str) or value["event_id"] != path.stem:
                raise ValueError("file/event identity mismatch")
            value["_parsed_at"] = utc(value.get("created_at_utc"))
            event_type = value.get("event_type")
            if not isinstance(event_type, str) or not event_type.strip():
                raise ValueError("missing event type")
            if value.get("work_item_status") not in {"OPEN", "IN_PROGRESS", "BLOCKED", "DONE"}:
                raise ValueError("unknown work item status")
            # Historical append-only events used types like CHECKPOINT and BLOCKER.
            # Their semantics are NOT in the current schema. Treat these as
            # opaque, substantive ordering barriers for their own work item;
            # never silently translate them to NOTE or infer execution rights.
            value["_opaque_event_type"] = event_type not in SUBSTANTIVE | {"NOTE"}
            records.append(value)
        except (OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError) as exc:
            errors.append(f"{path.name}: {type(exc).__name__}: {exc}")
    return records, errors


def evaluate(events: list[dict], *, now: datetime, stale_seconds: int) -> list[dict]:
    if stale_seconds < 60:
        raise ValueError("stale threshold must be at least 60 seconds")
    latest: dict[str, dict] = {}
    for event in events:
        if event["event_type"] == "NOTE":
            continue
        key = event["work_item_id"]
        current = latest.get(key)
        order = (event["_parsed_at"], event["event_id"])
        if current is None or order > (current["_parsed_at"], current["event_id"]):
            latest[key] = event
    results: list[dict] = []
    for work_item_id, event in sorted(latest.items()):
        status = event["work_item_status"]
        age = (now - event["_parsed_at"]).total_seconds()
        if event.get("_opaque_event_type"):
            # Unknown historical event is authoritative as an ordering
            # barrier, never an auto-resume proposal; even if status is OPEN.
            continue
        if age < -300:
            code = "CLOCK_OR_SNAPSHOT_ERROR"
        elif status in FINAL:
            continue
        elif age < stale_seconds:
            continue
        elif event["event_type"] == "RESULT" and event.get("outcome") == "PASS":
            code = "HANDOFF_REVIEW_REQUIRED" if (
                event.get("first_incomplete_step") and event.get("next_action")
            ) else "MISSING_NEXT_STEP"
        elif event["event_type"] == "RESULT" and event.get("outcome") == "FAIL":
            code = "FAILED_NEEDS_DIAGNOSIS"
        elif event["event_type"] in {"ATTEMPT", "PLAN"}:
            code = "UNVERIFIED_TASK_OR_DISPATCH"
        else:
            code = "STALE_NEEDS_REVIEW"
        # A report never grants authorization to repeat, continue, or skip an AI gate.
        raw_identity = json.dumps(
            [work_item_id, event["event_id"], code], separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        report_id = "CONTINUITY-" + hashlib.sha256(raw_identity).hexdigest()[:24]
        results.append({
            "schema": "PREDICTION_INDEPENDENT_CONTINUITY_REPORT_V1",
            "report_id": report_id,
            "work_item_id": work_item_id,
            "last_substantive_event_id": event["event_id"],
            "last_event_at_utc": event["created_at_utc"],
            # Exclude wall-clock age: immutable reports must stay byte-identical on rescans.
            "classification": code,
            "last_task_ids": event.get("task_ids") if isinstance(event.get("task_ids"), list) else [],
            "first_incomplete_step": event.get("first_incomplete_step"),
            "next_action_from_ledger": event.get("next_action"),
            "execution_authorized": False,
            "automatic_resubmission": False,
            "bridge_or_executor_mutation": False,
            "required_check": (
                "Verify immutable task/result/receipt and route evidence; check the "
                "latest canonical governance gates before creating any fresh action."
            ),
        })
    return results


def write_immutable(folder: Path, records: list[dict]) -> list[str]:
    """Exactly-once proposal files by content identity; never overwrite or delete."""
    folder.mkdir(parents=True, exist_ok=True)
    written = []
    for record in records:
        dest = folder / (record["report_id"] + ".json")
        content = (json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
        try:
            fd = os.open(str(dest), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            if dest.is_symlink() or dest.read_bytes() != content:
                raise ValueError("existing continuity report collision")
            continue
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        written.append(dest.name)
    return written


def scan(events_dir: Path, proposals_dir: Path | None, now: datetime, minutes: int) -> dict:
    events, errors = load_events(events_dir)
    # A malformed event can conceal a newer terminal state. Fail closed globally.
    reports = [] if errors else evaluate(events, now=now, stale_seconds=minutes * 60)
    written = write_immutable(proposals_dir, reports) if proposals_dir and not errors else []
    return {
        "schema": "PREDICTION_INDEPENDENT_CONTINUITY_SCAN_V1",
        "status": "INPUT_INVALID" if errors else "PASS",
        "observed_events": len(events),
        "opaque_event_count": sum(bool(e.get("_opaque_event_type")) for e in events),
        "errors": errors,
        "observations": reports,
        "new_report_files": written,
        "can_auto_execute": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events-dir", type=Path, required=True)
    parser.add_argument("--proposals-dir", type=Path)
    parser.add_argument("--stale-minutes", type=int, default=30)
    parser.add_argument("--once", action="store_true", help="scan once (default)")
    parser.add_argument("--interval-seconds", type=int, default=0, help="poll forever if > 0")
    args = parser.parse_args()
    if args.stale_minutes < 1 or args.interval_seconds < 0:
        parser.error("invalid interval")
    while True:
        try:
            result = scan(args.events_dir, args.proposals_dir, datetime.now(timezone.utc), args.stale_minutes)
        except (ValueError, OSError) as exc:
            print(json.dumps({"status": "INPUT_INVALID", "error": str(exc)}), flush=True)
            return 2
        print(json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
        if result["status"] != "PASS":
            return 2
        if args.interval_seconds == 0:
            return 0
        time.sleep(max(60, args.interval_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
