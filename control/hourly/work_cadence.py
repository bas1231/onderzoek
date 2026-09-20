from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import argparse
import json
import os
import tempfile
from typing import Any

STATE_PATH = Path.home() / ".local/state/prediction-research/work_cadence.json"
WORK_DURATION = timedelta(hours=4)
COOLDOWN_DURATION = timedelta(hours=1)
SCHEMA_VERSION = 1


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("cadence timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _atomic_write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def _new_work_state(now: datetime, reason: str) -> dict[str, Any]:
    work_until = now + WORK_DURATION
    cooldown_until = work_until + COOLDOWN_DURATION
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "WORK",
        "work_started_at": _iso(now),
        "work_until": _iso(work_until),
        "cooldown_until": _iso(cooldown_until),
        "last_transition_at": _iso(now),
        "last_reason": reason,
    }


def _load(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported cadence schema")
    return data


def check(
    *,
    now: datetime | None = None,
    state_path: Path = STATE_PATH,
    start_if_idle: bool = True,
    mutate: bool = True,
    reason: str = "hourly_research_task",
) -> dict[str, Any]:
    """Return a fail-closed work/cooldown decision.

    Missing state means no work block exists yet. The first active task starts a
    four-hour work block. Cooldown is anchored to the scheduled end of that
    block and lasts one full hour. A corrupt state never starts work.
    """
    current = (now or _utc_now()).astimezone(timezone.utc)

    try:
        state = _load(state_path)
    except Exception as exc:
        return {
            "allowed": False,
            "mode": "ERROR",
            "reason": "CADENCE_STATE_INVALID",
            "error": f"{type(exc).__name__}: {exc}",
            "state_path": str(state_path),
        }

    if state is None:
        if not start_if_idle:
            return {
                "allowed": True,
                "mode": "IDLE",
                "reason": "NO_ACTIVE_BLOCK",
                "state_path": str(state_path),
            }
        state = _new_work_state(current, reason)
        if mutate:
            _atomic_write(state_path, state)
        return {
            "allowed": True,
            "mode": "WORK",
            "reason": "WORK_BLOCK_STARTED",
            "state_path": str(state_path),
            **state,
        }

    work_until = _parse(state.get("work_until"))
    cooldown_until = _parse(state.get("cooldown_until"))
    if work_until is None or cooldown_until is None:
        return {
            "allowed": False,
            "mode": "ERROR",
            "reason": "CADENCE_STATE_INCOMPLETE",
            "state_path": str(state_path),
        }

    if current < work_until:
        state["mode"] = "WORK"
        return {
            "allowed": True,
            "reason": "WITHIN_WORK_BLOCK",
            "state_path": str(state_path),
            **state,
        }

    if current < cooldown_until:
        if state.get("mode") != "COOLDOWN":
            state["mode"] = "COOLDOWN"
            state["last_transition_at"] = _iso(current)
            state["last_reason"] = "four_hour_limit_reached"
            if mutate:
                _atomic_write(state_path, state)
        return {
            "allowed": False,
            "reason": "COOLDOWN_ACTIVE",
            "state_path": str(state_path),
            **state,
        }

    if not start_if_idle:
        return {
            "allowed": True,
            "mode": "IDLE",
            "reason": "COOLDOWN_COMPLETE",
            "state_path": str(state_path),
            **state,
        }

    state = _new_work_state(current, reason)
    if mutate:
        _atomic_write(state_path, state)
    return {
        "allowed": True,
        "mode": "WORK",
        "reason": "NEW_WORK_BLOCK_STARTED_AFTER_COOLDOWN",
        "state_path": str(state_path),
        **state,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", action="store_true", help="Read only; do not start a new block")
    args = parser.parse_args()
    result = check(start_if_idle=not args.status, mutate=not args.status)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("allowed") else 75


if __name__ == "__main__":
    raise SystemExit(main())
