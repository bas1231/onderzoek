from pathlib import Path


ROOT = Path.cwd()


def test_hourly_cycle_schedules_and_builds_ai_bundle_before_wake():
    source = (
        ROOT / "control/hourly/hourly_cycle.py"
    ).read_text(encoding="utf-8")

    graph_call = "graph.record_cycle_inputs"
    schedule_call = "scheduler.schedule(packet_dir)"
    build_call = "ai_handoff.build(run['run_id'])"
    wake_call = "control/hourly/hourly_wake.py"

    for call in (graph_call, schedule_call, build_call, wake_call):
        assert call in source

    assert source.index(graph_call) < source.index(schedule_call)
    assert source.index(schedule_call) < source.index(build_call)
    assert source.index(build_call) < source.index(wake_call)
    assert "'ai_work_bundle_ref'" in source
    assert "'ai_work_ready_roles'" in source
    assert "'ai_work_job_count'" in source
    assert "'scheduled_dynamic_workers'" in source
    assert "'scheduled_transient_workers'" in source


def test_hourly_cycle_keeps_ai_path_out_of_executor_and_safety_closed():
    source = (
        ROOT / "control/hourly/hourly_cycle.py"
    ).read_text(encoding="utf-8")

    assert "ai_handoff" in source
    assert "E007_SIX_DOMAIN" in source
    assert "live_trading': False" in source
    assert "paid_actions': False" in source
    assert "wallet_actions': False" in source
    assert "openai_api': False" in source
