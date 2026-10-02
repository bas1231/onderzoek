from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "PREDICTION_CONTINUATION_V2"
MAX_ATTEMPTS = 4
RETRY_AFTER_SECONDS = 120.0
CLAIM_STALE_SECONDS = 300.0

TERMINAL_STATES = {
    "NEXT_TASK_ACCEPTED",
    "DONE",
    "BLOCKED",
    "CONFLICT",
    "BLOCKED_TRANSPORT",
}


def _atomic_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _load_json(path: Path) -> dict | None:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def _digest(source_task_id: str) -> str:
    return hashlib.sha256(source_task_id.encode("utf-8")).hexdigest()[:24]


def ids_for(source_task_id: str) -> dict[str, str]:
    digest = _digest(source_task_id)
    return {
        "continuation_id": f"CONT-{digest}",
        "expected_next_task_id": f"DEV-PRED-CONT-NEXT-{digest}",
        "expected_done_task_id": f"CONT-DONE-{digest}",
        "expected_blocked_task_id": f"CONT-BLOCKED-{digest}",
    }


def continuation_dir(data_dir: Path) -> Path:
    return data_dir / "continuations"


def continuation_path(data_dir: Path, continuation_id: str) -> Path:
    return continuation_dir(data_dir) / f"{continuation_id}.json"


def command_state(task_state_dir: Path, task_id: str) -> dict | None:
    return _load_json(task_state_dir / f"{task_id}.json")


def source_allows_auto_continue(task_state_dir: Path, task_id: str) -> bool:
    state = command_state(task_state_dir, task_id)
    return bool(state and state.get("auto_continue") is True)


def _append_history(record: dict, state: str, detail: str) -> None:
    now = time.time()
    record["state"] = state
    record["updated_at"] = now
    record.setdefault("history", []).append({
        "at": now,
        "state": state,
        "detail": str(detail)[:500],
    })


def start_for_result_ack(
    *,
    data_dir: Path,
    task_state_dir: Path,
    source_task_id: str,
    chat_id: str,
) -> dict | None:
    if not source_allows_auto_continue(task_state_dir, source_task_id):
        return None

    ids = ids_for(source_task_id)
    path = continuation_path(data_dir, ids["continuation_id"])
    existing = _load_json(path)
    if existing:
        return existing

    now = time.time()
    record = {
        "schema": SCHEMA,
        **ids,
        "source_task_id": source_task_id,
        "chat_id": chat_id,
        "expected_route_task_id": source_task_id,
        "state": "CONTINUE_REQUESTED",
        "attempts": 0,
        "last_attempt_at": None,
        "created_at": now,
        "updated_at": now,
        "history": [{
            "at": now,
            "state": "CONTINUE_REQUESTED",
            "detail": "source result ACKed in originating chat",
        }],
    }
    _atomic_json(path, record)
    return record


def _outcome_candidates(record: dict, task_state_dir: Path) -> list[tuple[str, dict]]:
    out: list[tuple[str, dict]] = []
    mapping = (
        ("NEXT", "expected_next_task_id"),
        ("DONE", "expected_done_task_id"),
        ("BLOCKED", "expected_blocked_task_id"),
    )
    for label, key in mapping:
        state = command_state(task_state_dir, str(record[key]))
        if state is not None:
            out.append((label, state))
    return out


def _claimed_is_stale(state: dict, now: float | None = None) -> bool:
    raw = str(state.get("claimed_at_utc") or "").strip()
    if not raw:
        return False
    try:
        claimed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return False
    if claimed.tzinfo is None:
        claimed = claimed.replace(tzinfo=timezone.utc)
    current = time.time() if now is None else float(now)
    return current - claimed.timestamp() >= CLAIM_STALE_SECONDS


def reconcile(record: dict, task_state_dir: Path, now: float | None = None) -> bool:
    if record.get("state") in TERMINAL_STATES:
        return False

    candidates = _outcome_candidates(record, task_state_dir)
    if len(candidates) > 1:
        _append_history(
            record,
            "CONFLICT",
            "multiple mutually exclusive downstream outcome task IDs exist",
        )
        return True

    if not candidates:
        return False

    label, state = candidates[0]
    status = str(state.get("status") or "")

    if label == "NEXT":
        if status == "CLAIMED":
            if _claimed_is_stale(state, now):
                _append_history(record, "BLOCKED", "expected child command remained CLAIMED past bounded timeout")
                return True
            if record.get("state") != "NEXT_TASK_CREATED":
                _append_history(record, "NEXT_TASK_CREATED", "expected child command claimed")
                return True
            return False
        if status == "DISPATCHED":
            _append_history(record, "NEXT_TASK_ACCEPTED", "expected child command dispatched")
            return True
        if status in {"REJECTED", "BLOCKED_ROUTE", "AMBIGUOUS"}:
            _append_history(record, "BLOCKED", f"expected child command ended {status}")
            return True
        return False

    if status == "CLAIMED":
        if _claimed_is_stale(state, now):
            _append_history(record, "BLOCKED", f"{label.lower()} receipt remained CLAIMED past bounded timeout")
            return True
        target = f"{label}_RECEIPT_CREATED"
        if record.get("state") != target:
            _append_history(record, target, f"{label.lower()} receipt claimed")
            return True
        return False

    if status == "DISPATCHED":
        _append_history(record, label, f"{label.lower()} receipt dispatched")
        return True

    if status in {"REJECTED", "BLOCKED_ROUTE", "AMBIGUOUS"}:
        _append_history(record, "BLOCKED", f"{label.lower()} receipt ended {status}")
        return True

    return False


def _attempt_task_id(record: dict, attempt: int) -> str:
    digest = str(record["continuation_id"]).removeprefix("CONT-")
    return f"CONT-WAKE-{digest}-A{attempt:02d}"


def mark_delivery_acked(*, data_dir: Path, event: dict) -> bool:
    if str(event.get("source") or "") != "control_continuation_v2":
        return False

    continuation_id = str(event.get("continuation_id") or "")
    if not continuation_id:
        return False

    path = continuation_path(data_dir, continuation_id)
    record = _load_json(path)
    if not record or record.get("schema") != SCHEMA:
        return False

    try:
        attempt = int(event.get("attempt") or 0)
    except (TypeError, ValueError):
        return False
    if attempt <= 0:
        return False

    previous = int(record.get("last_acked_attempt") or 0)
    if attempt <= previous:
        return True

    now = time.time()
    record["last_acked_attempt"] = attempt
    record["last_delivery_acked_at"] = now
    record["updated_at"] = now
    if record.get("state") not in TERMINAL_STATES:
        _append_history(record, "CONTINUE_SENT", f"delivery attempt {attempt} ACKed by browser agent")
    _atomic_json(path, record)
    return True


def _delivery_still_pending(
    record: dict,
    data_dir: Path,
    *,
    now: float | None = None,
) -> bool:
    """Return whether the latest delivery attempt still owns the transport slot.

    OUTBOX is always left alone: if no browser has leased the event, creating
    more copies cannot improve delivery.

    INFLIGHT is different for continuation events. The generic wake queue is
    deliberately at-most-once and never requeues ambiguous inflight results.
    A continuation prompt is safe to retry because all downstream outcomes use
    deterministic task IDs. Therefore only a stale, identity-matching
    continuation inflight event may be retired to an evidence-preserving
    abandoned directory so a fresh delivery ID can be created.
    """
    event_id = str(record.get("last_event_id") or "")
    if not event_id:
        return False

    outbox = data_dir / "outbox" / f"{event_id}.json"
    if outbox.exists():
        return True

    inflight = data_dir / "inflight" / f"{event_id}.json"
    if not inflight.exists():
        return False

    event = _load_json(inflight)
    if not event:
        return True

    if (
        str(event.get("source") or "") != "control_continuation_v2"
        or str(event.get("continuation_id") or "") != str(record.get("continuation_id") or "")
        or str(event.get("event_id") or "") != event_id
    ):
        return True

    current = time.time() if now is None else float(now)
    try:
        created_at = float(event.get("created_at"))
    except (TypeError, ValueError):
        try:
            created_at = inflight.stat().st_mtime
        except OSError:
            return False

    if current - created_at < RETRY_AFTER_SECONDS:
        return True

    abandoned = data_dir / "continuation_abandoned"
    abandoned.mkdir(parents=True, exist_ok=True)
    destination = abandoned / inflight.name

    try:
        os.replace(inflight, destination)
    except FileNotFoundError:
        return False

    record["last_abandoned_event_id"] = event_id
    _append_history(
        record,
        "DELIVERY_AMBIGUOUS",
        f"stale continuation inflight {event_id} retired before retry",
    )
    _atomic_json(
        continuation_path(data_dir, str(record["continuation_id"])),
        record,
    )
    return False


def _attempt_message(record: dict, attempt: int) -> str:
    return (
        "PREDICTION_CONTROL_CONTINUE_V2\n"
        f"continuation_id={record['continuation_id']}\n"
        f"source_task_id={record['source_task_id']}\n"
        f"attempt={attempt}\n"
        "No human input is required. Inspect the current Prediction source of truth and select exactly one durable outcome.\n"
        f"NEXT: create the next authorized Prediction task using exactly task_id={record['expected_next_task_id']}; "
        "for project work use that same ID in project task, DEV manifest and command-bus inbox; "
        f"use route_task_id={record['expected_route_task_id']}; set auto_continue=true "
        f"and parent_continuation_id={record['continuation_id']}. If that exact task already exists, do not modify or replace it.\n"
        f"DONE: create exactly one headless BRIDGE_PING command-bus receipt with task_id={record['expected_done_task_id']}, "
        f"delivery_mode=headless, auto_continue=false and parent_continuation_id={record['continuation_id']}.\n"
        f"BLOCKED: create exactly one headless BRIDGE_PING command-bus receipt with task_id={record['expected_blocked_task_id']}, "
        f"delivery_mode=headless, auto_continue=false and parent_continuation_id={record['continuation_id']}.\n"
        "Never create more than one of NEXT/DONE/BLOCKED. Browser send/ACK is not success; the durable command-bus state is authoritative."
    )


def enqueue_attempt(
    *,
    record: dict,
    data_dir: Path,
    routes_dir: Path,
    outbox_dir: Path,
    now: float | None = None,
) -> bool:
    if record.get("state") in TERMINAL_STATES or record.get("state") in {"NEXT_TASK_CREATED", "DONE_RECEIPT_CREATED", "BLOCKED_RECEIPT_CREATED"}:
        return False

    now = time.time() if now is None else float(now)
    attempts = int(record.get("attempts") or 0)
    last = record.get("last_delivery_acked_at") or record.get("last_attempt_at")

    if _delivery_still_pending(record, data_dir, now=now):
        return False

    if attempts >= MAX_ATTEMPTS:
        _append_history(record, "BLOCKED_TRANSPORT", "continuation exhausted bounded delivery attempts")
        _atomic_json(continuation_path(data_dir, record["continuation_id"]), record)
        return False

    if last is not None and now - float(last) < RETRY_AFTER_SECONDS:
        return False

    attempt = attempts + 1
    attempt_task_id = _attempt_task_id(record, attempt)
    event_id = f"cont-{int(now * 1000)}-{secrets.token_hex(4)}"
    message = _attempt_message(record, attempt)

    _atomic_json(routes_dir / f"{attempt_task_id}.json", {
        "version": 2,
        "task_id": attempt_task_id,
        "chat_id": record["chat_id"],
        "consumer_id": None,
        "source": "control_continuation_v2",
        "created_at_unix": now,
        "continuation_id": record["continuation_id"],
        "attempt": attempt,
    })
    _atomic_json(outbox_dir / f"{event_id}.json", {
        "event_id": event_id,
        "task_id": attempt_task_id,
        "message": message,
        "created_at": now,
        "source": "control_continuation_v2",
        "continuation_id": record["continuation_id"],
        "attempt": attempt,
    })

    record["attempts"] = attempt
    record["last_attempt_at"] = now
    record["last_event_id"] = event_id
    record["last_attempt_task_id"] = attempt_task_id
    _append_history(record, "CONTINUE_QUEUED", f"delivery attempt {attempt} queued as {attempt_task_id}")
    _atomic_json(continuation_path(data_dir, record["continuation_id"]), record)
    return True


def maintain_for_chat(
    *,
    data_dir: Path,
    task_state_dir: Path,
    routes_dir: Path,
    outbox_dir: Path,
    chat_id: str,
    now: float | None = None,
) -> None:
    root = continuation_dir(data_dir)
    if not root.exists():
        return

    for path in sorted(root.glob("CONT-*.json")):
        record = _load_json(path)
        if not record or record.get("schema") != SCHEMA:
            continue
        if str(record.get("chat_id") or "") != str(chat_id):
            continue

        changed = reconcile(record, task_state_dir, now=now)
        if changed:
            _atomic_json(path, record)

        if record.get("state") in TERMINAL_STATES:
            continue

        enqueue_attempt(
            record=record,
            data_dir=data_dir,
            routes_dir=routes_dir,
            outbox_dir=outbox_dir,
            now=now,
        )
