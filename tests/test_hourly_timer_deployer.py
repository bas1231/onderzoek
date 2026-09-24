from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "control/jobs/deploy_hourly_runtime_sync_e001.py"
SERVICE = ROOT / "control/hourly/systemd/prediction-research-hourly-director.service"


def test_deployer_installs_service_and_timer_and_activates_timer():
    text = DEPLOY.read_text(encoding="utf-8")
    assert 'prediction-research-hourly-director.service' in text
    assert 'prediction-research-hourly-director.timer' in text
    assert 'enable","--now","prediction-research-hourly-director.timer' in text
    assert 'is-active","prediction-research-hourly-director.timer' in text
    assert 'is-enabled","prediction-research-hourly-director.timer' in text


def test_deployer_verifies_canonical_timer_contract():
    text = DEPLOY.read_text(encoding="utf-8")
    assert 'OnCalendar=*-*-* *:00:00' in text
    assert 'Persistent=true' in text
    assert 'installed timer is stale or malformed' in text


def test_service_and_deployer_require_prod_runtime_path():
    service = SERVICE.read_text(encoding="utf-8")
    deploy = DEPLOY.read_text(encoding="utf-8")

    required = (
        "WorkingDirectory=%h/prediction_research_prod",
        "ExecStartPre=%h/prediction_research_prod/.venv/bin/python %h/prediction_research_prod/control/hourly/runtime_sync.py",
        "ExecStart=%h/prediction_research_prod/.venv/bin/python %h/prediction_research_prod/control/hourly/edge_hunter_cycle.py",
        "ExecStartPost=%h/prediction_research_prod/.venv/bin/python %h/prediction_research_prod/control/hourly/runtime_health.py",
    )
    for line in required:
        assert line in service
        assert line in deploy

    assert "%h/prediction_research/" not in service
    assert "WorkingDirectory=/home/leonh/prediction_research" not in service
