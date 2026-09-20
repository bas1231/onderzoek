from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from control.hourly import work_cadence


def at(hours: int, minutes: int = 0, seconds: int = 0) -> datetime:
    return datetime(2026, 9, 20, hours, minutes, seconds, tzinfo=timezone.utc)


def test_first_task_starts_four_hour_block(tmp_path: Path) -> None:
    state = tmp_path / "cadence.json"
    result = work_cadence.check(now=at(8), state_path=state)
    assert result["allowed"] is True
    assert result["mode"] == "WORK"
    assert result["work_started_at"] == "2026-09-20T08:00:00Z"
    assert result["work_until"] == "2026-09-20T12:00:00Z"
    assert result["cooldown_until"] == "2026-09-20T13:00:00Z"


def test_last_second_before_limit_is_allowed(tmp_path: Path) -> None:
    state = tmp_path / "cadence.json"
    work_cadence.check(now=at(8), state_path=state)
    result = work_cadence.check(now=at(11, 59, 59), state_path=state)
    assert result["allowed"] is True
    assert result["reason"] == "WITHIN_WORK_BLOCK"


def test_exact_four_hour_boundary_enters_cooldown(tmp_path: Path) -> None:
    state = tmp_path / "cadence.json"
    work_cadence.check(now=at(8), state_path=state)
    result = work_cadence.check(now=at(12), state_path=state)
    assert result["allowed"] is False
    assert result["mode"] == "COOLDOWN"
    assert result["reason"] == "COOLDOWN_ACTIVE"


def test_cooldown_blocks_entire_hour(tmp_path: Path) -> None:
    state = tmp_path / "cadence.json"
    work_cadence.check(now=at(8), state_path=state)
    assert work_cadence.check(now=at(12, 30), state_path=state)["allowed"] is False
    assert work_cadence.check(now=at(12, 59, 59), state_path=state)["allowed"] is False


def test_exact_cooldown_end_starts_new_block(tmp_path: Path) -> None:
    state = tmp_path / "cadence.json"
    work_cadence.check(now=at(8), state_path=state)
    result = work_cadence.check(now=at(13), state_path=state)
    assert result["allowed"] is True
    assert result["reason"] == "NEW_WORK_BLOCK_STARTED_AFTER_COOLDOWN"
    assert result["work_started_at"] == "2026-09-20T13:00:00Z"
    assert result["work_until"] == "2026-09-20T17:00:00Z"


def test_status_mode_does_not_create_state(tmp_path: Path) -> None:
    state = tmp_path / "cadence.json"
    result = work_cadence.check(
        now=at(8),
        state_path=state,
        start_if_idle=False,
        mutate=False,
    )
    assert result["allowed"] is True
    assert result["mode"] == "IDLE"
    assert state.exists() is False


def test_corrupt_state_fails_closed(tmp_path: Path) -> None:
    state = tmp_path / "cadence.json"
    state.write_text("not-json")
    result = work_cadence.check(now=at(8), state_path=state)
    assert result["allowed"] is False
    assert result["mode"] == "ERROR"
    assert result["reason"] == "CADENCE_STATE_INVALID"


def test_cooldown_is_anchored_to_scheduled_work_end(tmp_path: Path) -> None:
    state = tmp_path / "cadence.json"
    work_cadence.check(now=at(8), state_path=state)
    result = work_cadence.check(now=at(12, 45), state_path=state)
    assert result["allowed"] is False
    assert result["cooldown_until"] == "2026-09-20T13:00:00Z"


def test_long_idle_after_cooldown_starts_from_actual_next_task(tmp_path: Path) -> None:
    state = tmp_path / "cadence.json"
    work_cadence.check(now=at(8), state_path=state)
    result = work_cadence.check(now=at(15), state_path=state)
    assert result["allowed"] is True
    assert result["work_started_at"] == "2026-09-20T15:00:00Z"
    assert result["work_until"] == "2026-09-20T19:00:00Z"
