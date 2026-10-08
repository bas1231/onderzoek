"""Standalone continuity-to-existing-dashboard-launch coordinator.

This module changes NO bridge/executor code or configuration. In --emit mode
it publishes ONLY the already-defined DASHBOARD_NEW_SESSION_LAUNCH_V1 message
contract. Default is dry-run. Never submits project tasks, replays a result or
asserts an Astra/Sol approval. Source freshness and event identity are checked.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import time
from urllib.parse import urlparse

try:
    from control.independent_continuity.observer import evaluate, load_events
except ModuleNotFoundError:
    from observer import evaluate, load_events

MAX_JSON = 1024 * 1024
TASK_RE = re.compile(r"^[a-zA-Z0-9._:-]{1,160}$")
HEX24 = re.compile(r"^[a-f0-9]{24}$")
SCHEMA = "PREDICTION_INDEPENDENT_CONTINUITY_REPORT_V1"
EVENT_KIND = "DASHBOARD_NEW_SESSION_LAUNCH_V1"


class UnsafeLaunch(ValueError):
    pass


def read_safe(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_JSON:
        raise UnsafeLaunch("invalid or oversized JSON input")
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise UnsafeLaunch("JSON object required")
    return obj


def write_exclusive(path: Path, obj: dict) -> None:
    """Durably create a single new file; never replace another producer's file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink() or path.is_symlink():
        raise UnsafeLaunch("symlink destination forbidden")
    raw = (json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode()
    fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def verify_source_fresh(fetch_head: Path, *, now_unix: float, max_age: int = 180) -> None:
    if fetch_head.is_symlink() or not fetch_head.is_file():
        raise UnsafeLaunch("fresh source snapshot missing")
    age = now_unix - fetch_head.stat().st_mtime
    if age < -10 or age > max_age:
        raise UnsafeLaunch("source snapshot stale or clock invalid")


def verified_report(report_path: Path, events_dir: Path, *, now: datetime,
                    stale_minutes: int = 30) -> dict:
    """Never trust a proposal without re-deriving it from the latest ledger."""
    if now.tzinfo is None:
        raise UnsafeLaunch("timezone required")
    given = read_safe(report_path)
    if given.get("schema") != SCHEMA or given.get("execution_authorized") is not False:
        raise UnsafeLaunch("untrusted or execution-authorizing report")
    if given.get("automatic_resubmission") is not False:
        raise UnsafeLaunch("resubmission flag forbidden")
    events, errors = load_events(events_dir)
    if errors:
        raise UnsafeLaunch("invalid ledger events; fail closed")
    candidates = evaluate(events, now=now, stale_seconds=stale_minutes * 60)
    matches = [r for r in candidates if r["report_id"] == given.get("report_id")]
    if len(matches) != 1 or matches[0] != given:
        raise UnsafeLaunch("report is not the current, exact ledger-derived proposal")
    if given.get("classification") == "CLOCK_OR_SNAPSHOT_ERROR":
        raise UnsafeLaunch("time anomaly")
    item = str(given.get("work_item_id", ""))
    if not TASK_RE.fullmatch(item):
        raise UnsafeLaunch("work item id invalid")
    return given


def fresh_launcher(bridge_data: Path, *, now_unix: float) -> dict:
    """Match an active browser launcher to an actually SENT chat route."""
    sent_root = bridge_data / "sent"
    route_root = bridge_data / "routes"
    launch_root = bridge_data / "dashboard_launchers"
    if any(not p.is_dir() or p.is_symlink() for p in (sent_root, route_root, launch_root)):
        raise UnsafeLaunch("existing browser launcher/runtime not available")
    # Match the dashboard's latest proven SENT chat route, not any older
    # still-registered launcher. Otherwise a stale tab could unexpectedly
    # receive a new-session recovery event after active chat changed.
    latest_proven = None
    sent_files = sorted(
        (p for p in sent_root.glob("*.json") if p.is_file() and not p.is_symlink()),
        key=lambda p: p.stat().st_mtime_ns, reverse=True
    )
    for path in sent_files[:2000]:
        try:
            event = read_safe(path)
            task = str(event.get("task_id") or "")
            if not TASK_RE.fullmatch(task):
                continue
            route = read_safe(route_root / (task + ".json"))
            chat, consumer = route.get("chat_id"), route.get("consumer_id")
            if chat and consumer and not str(chat).startswith("HEADLESS"):
                latest_proven = (chat, consumer)
                break
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    if latest_proven is None:
        raise UnsafeLaunch("NO_PROVEN_LATEST_CHAT_ROUTE")
    available = []
    for path in launch_root.glob("*.json"):
        try:
            obj = read_safe(path)
            chat, consumer = obj.get("chat_id"), obj.get("consumer_id")
            if obj.get("schema") != "PREDICTION_DASHBOARD_LAUNCHER_V1":
                continue
            if (chat, consumer) != latest_proven:
                continue
            if "dashboard_new_session_launch_v1" not in obj.get("capabilities", []):
                continue
            last = obj.get("updated_at_unix")
            if not isinstance(last, (int, float)) or not 0 <= now_unix - last <= 180:
                continue
            parsed = urlparse(str(obj.get("launch_base_url") or ""))
            if (parsed.scheme != "https" or parsed.netloc != "chatgpt.com"
                    or not parsed.path.startswith("/g/g-p-") or "/c/" in parsed.path
                    or parsed.query or parsed.fragment):
                continue
            if not TASK_RE.fullmatch(str(chat)) or not TASK_RE.fullmatch(str(consumer)):
                continue
            available.append(obj)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            continue
    if not available:
        raise UnsafeLaunch("NEW_SESSION_LAUNCHER_NOT_READY")
    return max(available, key=lambda x: x["updated_at_unix"])


def recovery_prompt(report: dict) -> str:
    # Never insert ledger freeform fields as executable instructions.
    item = report["work_item_id"]
    event = report["last_substantive_event_id"]
    rid = report["report_id"]
    return (
        "PREDICTION_INDEPENDENT_CONTINUITY_RECOVERY_V1\n"
        f"work_item_id={item}\n"
        f"last_substantive_event_id={event}\n"
        f"continuity_report_id={rid}\n"
        "dashboard_session_policy=NEW_CHAT_REQUIRED\n"
        "You are starting a fresh Prediction-project ChatGPT session because an "
        "independent read-only observer flagged stale progress. This is an "
        "INVESTIGATION REQUEST ONLY, not build/trade/test authorization.\n"
        "Read the current canonical GitHub start guide, bridge freeze, build log, "
        "science/model gates and immutable task/result evidence. Determine whether "
        "this work item really stopped, has progressed, is blocked or is done.\n"
        "Wait until THIS fresh chat receives SESSION-ROUTE-* status=PASS exit=0 "
        "kind=SESSION_ROUTE_BOOTSTRAP before dispatching WSL tasks.\n"
        "Never reuse the old session route or task IDs, never retry ambiguous "
        "execution, never bypass Sol/Astra pre/post review, and never repeat "
        "completed work. Never edit bridge/executor, run paid actions, trade, "
        "move funds, read credentials or push Git from WSL.\n"
        "If genuinely incomplete, record verified first incomplete step and "
        "continue through already-authorized canonical capabilities only; "
        "otherwise document DONE/BLOCKED. Keep stable work_item_id and write "
        "append-only build-log RESULT/HANDOFF."
    )


def check_launch_budget(state_dir: Path, *, work_item: str, now_unix: float,
                        max_per_day: int = 3, min_gap_seconds: int = 1800) -> None:
    claims = state_dir / "claims"
    if not claims.is_dir():
        return
    matching = []
    for path in claims.glob("*.json"):
        row = read_safe(path)
        if row.get("work_item_id") != work_item:
            continue
        created = row.get("created_at_unix")
        if not isinstance(created, (int, float)):
            raise UnsafeLaunch("invalid launch history")
        if created > now_unix + 10:
            raise UnsafeLaunch("future launch history")
        matching.append(created)
    if any(now_unix - t < min_gap_seconds for t in matching):
        raise UnsafeLaunch("launch cooldown")
    if sum(now_unix - t <= 86400 for t in matching) >= max_per_day:
        raise UnsafeLaunch("daily launch limit")


def prepare(report: dict, launcher: dict, *, now_unix: float) -> dict:
    token = secrets.token_hex(12)
    assert HEX24.fullmatch(token)
    request_id = f"RECOVERY-{token}"
    task_id = f"CONTROL-RECOVERY-LAUNCH-{token}"
    event_id = f"control-recovery-launch-{token}"
    launch = {
        "schema": "PREDICTION_DASHBOARD_CHAT_LAUNCH_V1",
        "launch_token": token, "request_id": request_id,
        "action": "CONTINUITY_INVESTIGATE",
        "work_item_id": report["work_item_id"],
        "prompt": recovery_prompt(report),
        "launch_base_url": launcher["launch_base_url"],
        "state": "QUEUED",
        "created_at_utc": datetime.fromtimestamp(now_unix, timezone.utc).isoformat(),
    }
    route = {
        "version": 2, "task_id": task_id,
        "chat_id": launcher["chat_id"],
        "consumer_id": launcher["consumer_id"],
        "source": "prediction_independent_continuity_existing_dashboard_launch_v1",
        "created_at_unix": now_unix, "request_id": request_id,
    }
    wake = {
        "event_id": event_id, "task_id": task_id, "kind": EVENT_KIND,
        "launch_token": token,
        "launch_base_url": launcher["launch_base_url"],
        "message": f"PREDICTION_DASHBOARD_NEW_SESSION_LAUNCH_V1 token={token}",
        "created_at": now_unix,
        "source": "prediction_independent_continuity_existing_dashboard_launch_v1",
        "request_id": request_id,
    }
    return {"request_id": request_id, "report_id": report["report_id"],
            "work_item_id": report["work_item_id"], "task_id": task_id,
            "event_id": event_id, "created_at_unix": now_unix,
            "launch": launch, "route": route, "wake": wake}


def publish_existing_contract(plan: dict, *, state_dir: Path, bridge_data: Path) -> dict:
    """Emit only by using the EXISTING dashboard launch file contract.

    Claim before publication. Ambiguous partial delivery is NEVER retried.
    No changes to pre-existing bridge files; only O_EXCL new protocol events.
    """
    if not bridge_data.is_dir() or bridge_data.is_symlink():
        raise UnsafeLaunch("bridge runtime unavailable")
    expected = ("dashboard_launches", "routes", "outbox")
    if any(not (bridge_data / p).is_dir() or (bridge_data / p).is_symlink() for p in expected):
        raise UnsafeLaunch("installed dashboard launch transport unavailable")
    claim = state_dir / "claims" / (plan["report_id"] + ".json")
    write_exclusive(claim, {
        "schema": "PREDICTION_INDEPENDENT_RECOVERY_CLAIM_V1",
        "report_id": plan["report_id"],
        "work_item_id": plan["work_item_id"],
        "request_id": plan["request_id"],
        "created_at_unix": plan["created_at_unix"],
        "delivery_state": "CLAIMED_MAY_BE_AMBIGUOUS",
    })
    try:
        write_exclusive(bridge_data / "dashboard_launches" /
                        (plan["launch"]["launch_token"] + ".json"), plan["launch"])
        write_exclusive(bridge_data / "routes" / (plan["task_id"] + ".json"), plan["route"])
        write_exclusive(bridge_data / "outbox" / (plan["event_id"] + ".json"), plan["wake"])
    except (OSError, ValueError) as exc:
        # Evidence-preserving: NEVER delete the claim or resend automatically.
        raise UnsafeLaunch(f"AMBIGUOUS_LAUNCH_DO_NOT_RETRY: {type(exc).__name__}") from exc
    return {"state": "NEW_SESSION_QUEUED_NOT_CONFIRMED", "request_id": plan["request_id"],
            "report_id": plan["report_id"], "event_id": plan["event_id"]}


def process_once(events_dir: Path, proposals_dir: Path, state_dir: Path,
                 bridge_data: Path, fetch_head: Path, scope: set[str],
                 *, now_unix: float, emit: bool = False, stale_minutes: int = 30) -> dict:
    if not scope:
        raise UnsafeLaunch("explicit work-item allowlist required")
    verify_source_fresh(fetch_head, now_unix=now_unix)
    now = datetime.fromtimestamp(now_unix, timezone.utc)
    events, errors = load_events(events_dir)
    if errors:
        raise UnsafeLaunch("invalid ledger events")
    generated = evaluate(events, now=now, stale_seconds=stale_minutes * 60)
    filtered = [r for r in generated if r["work_item_id"] in scope
                and r["classification"] != "CLOCK_OR_SNAPSHOT_ERROR"]
    if not filtered:
        return {"state": "NO_ELIGIBLE_STALE_WORK", "emitted": False}
    filtered.sort(key=lambda r: (r["last_event_at_utc"], r["work_item_id"]))
    for target in filtered:
        p = proposals_dir / (target["report_id"] + ".json")
        if not p.exists():
            continue
        report = verified_report(p, events_dir, now=now, stale_minutes=stale_minutes)
        if (state_dir / "claims" / (report["report_id"] + ".json")).exists():
            continue
        try:
            check_launch_budget(state_dir, work_item=report["work_item_id"], now_unix=now_unix)
        except UnsafeLaunch:
            continue
        launcher = fresh_launcher(bridge_data, now_unix=now_unix)
        if not emit:
            return {"state": "READY_DRY_RUN", "emitted": False,
                    "report_id": report["report_id"], "work_item_id": report["work_item_id"],
                    "launcher_verified": True, "uses_existing_dashboard_contract": True}
        plan = prepare(report, launcher, now_unix=now_unix)
        return {**publish_existing_contract(plan, state_dir=state_dir, bridge_data=bridge_data),
                "emitted": True}
    return {"state": "NO_ELIGIBLE_UNCLAIMED_WORK", "emitted": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events-dir", type=Path, required=True)
    parser.add_argument("--proposals-dir", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--bridge-data", type=Path, required=True)
    parser.add_argument("--fetch-head", type=Path, required=True)
    parser.add_argument("--scope-file", type=Path, required=True)
    parser.add_argument("--stale-minutes", type=int, default=30)
    parser.add_argument("--emit", action="store_true",
                        help="opt-in: publish EXISTING dashboard event, no bridge code modifications")
    args = parser.parse_args()
    try:
        raw = read_safe(args.scope_file)
        if raw.get("schema") != "PREDICTION_INDEPENDENT_CONTINUITY_SCOPE_V1":
            raise UnsafeLaunch("scope schema invalid")
        allowed = raw.get("work_item_ids")
        if not isinstance(allowed, list) or not allowed or not all(
                isinstance(x, str) and TASK_RE.fullmatch(x) for x in allowed):
            raise UnsafeLaunch("invalid explicit work item allowlist")
        outcome = process_once(
            args.events_dir, args.proposals_dir, args.state_dir,
            args.bridge_data, args.fetch_head, set(allowed),
            now_unix=time.time(), emit=args.emit, stale_minutes=args.stale_minutes
        )
        print(json.dumps(outcome, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"state": "BLOCKED_FAIL_CLOSED", "reason": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
