from __future__ import annotations

from control.hourly import hourly_cycle


class FakeCadence:
    @staticmethod
    def check(**kwargs):
        return {
            'allowed': False,
            'mode': 'COOLDOWN',
            'reason': 'COOLDOWN_ACTIVE',
            'work_started_at': '2026-09-20T08:00:00Z',
            'work_until': '2026-09-20T12:00:00Z',
            'cooldown_until': '2026-09-20T13:00:00Z',
        }


def test_cooldown_returns_before_loading_research_modules(monkeypatch) -> None:
    loaded = []

    def fake_load(name, path):
        loaded.append(name)
        if name == 'work_cadence':
            return FakeCadence()
        raise AssertionError(f'research module loaded during cooldown: {name}')

    monkeypatch.setattr(hourly_cycle, 'load', fake_load)
    rc = hourly_cycle.main()

    assert rc == 75
    assert loaded == ['work_cadence']
