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


def test_all_orchestrated_roles_have_ai_worker_contract():
    orchestrator = load(
        "worker_contract_orchestrator",
        ROOT / "control/hourly/agent_orchestrator.py",
    )
    handoff = load(
        "worker_contract_handoff",
        ROOT / "control/hourly/ai_handoff.py",
    )
    response = load(
        "worker_contract_response",
        ROOT / "control/hourly/ai_response.py",
    )

    orchestrated = set(orchestrator.PRIMARY_ROLES) | set(
        orchestrator.CONTROL_ROLES
    )
    handed_off = set(handoff.ROLE_ORDER)
    accepted = set(response.ALLOWED_ROLE_IDS)

    assert orchestrated <= handed_off
    assert handed_off <= accepted
    assert "recon_scout" in handed_off
    assert "recon_scout" in accepted


def test_ai_handoff_candidate_schema_has_no_kill_or_promotion_state():
    source = (
        ROOT / "control/hourly/ai_handoff.py"
    ).read_text(encoding="utf-8")

    schema_tail = source.split('"expected_response_schema":', 1)[1]
    assert "PROMOTION_CANDIDATE" not in schema_tail
    assert "CLOSED_NEGATIVE" not in schema_tail
