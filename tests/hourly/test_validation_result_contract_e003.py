import json
from pathlib import Path


ROOT = Path.cwd()


def test_ai_handoff_exposes_exact_validation_result_contract():
    source = (
        ROOT / "control/hourly/ai_handoff.py"
    ).read_text(encoding="utf-8")

    assert "VALIDATION_RESULT_CONTRACT_E003" in source
    assert '"status": "PASS|FAIL|INCONCLUSIVE|WAITING"' in source
    assert (
        '"mode": '
        '"QUICK_KILL|DEEP_FALSIFICATION|REPRODUCTION|null"'
        in source
    )
    assert "Never use result in place of the required status field." in source


def test_scheduled_worker_contract_matches_local_validator():
    data = json.loads(
        (
            ROOT / "control/hourly/scheduled_worker_contract.json"
        ).read_text(encoding="utf-8")
    )

    spec = data["local_exchange_request"]["validation_result_contract"]

    assert spec["required_fields"] == [
        "candidate_id",
        "status",
    ]
    assert spec["allowed_statuses"] == [
        "PASS",
        "FAIL",
        "INCONCLUSIVE",
        "WAITING",
    ]
    assert spec["optional_mode_values"] == [
        "QUICK_KILL",
        "DEEP_FALSIFICATION",
        "REPRODUCTION",
    ]
    assert "may not replace status" in spec["status_field_rule"]
