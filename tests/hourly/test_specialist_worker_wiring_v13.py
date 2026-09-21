from pathlib import Path


ROOT = Path.cwd()


def test_hourly_cycle_builds_ai_bundle_before_wake():
    source = (
        ROOT / "control/hourly/hourly_cycle.py"
    ).read_text(encoding="utf-8")

    build_call = "ai_handoff.build(run['run_id'])"
    wake_call = "control/hourly/hourly_wake.py"

    assert build_call in source
    assert wake_call in source
    assert source.index(build_call) < source.index(wake_call)
    assert "'ai_work_bundle_ref'" in source
    assert "'ai_work_ready_roles'" in source
    assert "'ai_work_job_count'" in source


def test_hourly_cycle_keeps_ai_path_out_of_executor():
    source = (
        ROOT / "control/hourly/hourly_cycle.py"
    ).read_text(encoding="utf-8")

    assert "ai_handoff" in source
    assert "AI-only work bundle" in source
    assert "live_trading': False" in source
    assert "paid_actions': False" in source
    assert "wallet_actions': False" in source
