from __future__ import annotations

from control.jobs import watchdog_v1 as watchdog


def test_hard_guardrail_constants() -> None:
    assert watchdog.MAX_REPAIRS_PER_KEY == 3
    assert watchdog.PENDING_STALE_SECONDS == 90
    assert watchdog.RESULT_STALE_SECONDS == 90
    assert watchdog.HEARTBEAT_STALE_SECONDS == 90


def test_services_are_local_control_services_only() -> None:
    assert set(watchdog.SERVICES) == {
        'prediction-research-executor.service',
        'prediction-research-browser-bridge.service',
    }


def test_repair_budget_blocks_fourth_attempt() -> None:
    repairs = {'x': {'count': 3, 'last': 0}}
    assert watchdog.repair_allowed('x', repairs, 1000000) is False


def test_repair_budget_allows_first_attempt() -> None:
    assert watchdog.repair_allowed('new', {}, 1000000) is True
