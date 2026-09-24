from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WRAPPER = ROOT / "control/hourly/edge_hunter_cycle.py"
SERVICE = ROOT / "control/hourly/systemd/prediction-research-hourly-director.service"


def source() -> str:
    return WRAPPER.read_text(encoding="utf-8")


def test_wrapper_does_not_run_hourly_cycle_as_dunder_main():
    text = source()
    assert "runpy.run_path" not in text
    assert "hourly.main()" in text


def test_wrapper_propagates_cooldown_and_checkpoint_failures():
    text = source()
    assert "cycle_rc == 75" in text
    assert "return 75" in text
    assert "if proc.returncode != 0" in text
    assert "raise RuntimeError" in text


def test_latest_run_selection_requires_canonical_manifest_identity():
    text = source()
    assert 'data.get("run_id") == stem' in text
    ast.parse(text)


def test_systemd_treats_only_cadence_75_as_successful_no_work():
    unit = SERVICE.read_text(encoding="utf-8")
    assert "SuccessExitStatus=75" in unit
    assert "ExecStartPre=" in unit
    assert "runtime_sync.py" in unit
    assert "edge_hunter_cycle.py" in unit
