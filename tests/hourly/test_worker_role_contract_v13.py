import importlib.util
import sys
from pathlib import Path


ROOT = Path.cwd()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_six_domain_runtime_roles_have_ai_worker_contract():
    architecture = load(
        "worker_contract_architecture",
        ROOT / "control/hourly/research_os_architecture.py",
    )
    handoff = load(
        "worker_contract_handoff",
        ROOT / "control/hourly/ai_handoff.py",
    )
    response = load(
        "worker_contract_response",
        ROOT / "control/hourly/ai_response.py",
    )

    expected_permanent = set(architecture.PERMANENT_AGENTS)
    expected_transient = {"independent_reproducer"}
    expected = expected_permanent | expected_transient
    handed_off = set(handoff.ROLE_ORDER)
    accepted = set(response.ALLOWED_ROLE_IDS)

    assert expected_permanent == {
        "discovery",
        "market_research",
        "mechanics",
        "algebra",
        "red_team_pentest",
        "research_director",
    }
    assert handed_off == expected
    assert accepted == expected

    legacy_permanent_roles = {
        "recon_scout",
        "scout",
        "settlement",
        "microstructure",
        "behavioral",
        "informed_flow",
        "weather_twc",
        "prebuild_killer",
        "chief_falsifier",
    }
    assert not legacy_permanent_roles.intersection(handed_off)
    assert not legacy_permanent_roles.intersection(accepted)


def test_ai_handoff_candidate_schema_has_no_kill_or_promotion_state():
    source = (
        ROOT / "control/hourly/ai_handoff.py"
    ).read_text(encoding="utf-8")

    schema_tail = source.split('"expected_response_schema":', 1)[1]
    assert "PROMOTION_CANDIDATE" not in schema_tail
    assert "CLOSED_NEGATIVE" not in schema_tail
