import pytest

from control.research_os_v1.prospective_collector import build_cycle_capture
from control.research_os_v1.prospective_resolver import resolve_case


def candidate(
    cid: str,
    *,
    queue_status: str = "RUNNING",
    economic_status: str = "NO_PROVEN_EDGE",
    gate_state: str = "PENDING",
):
    return {
        "candidate_id": cid,
        "hypothesis": f"hypothesis {cid}",
        "queue_status": queue_status,
        "economic_status": economic_status,
        "priority": "P2",
        "required_gates": {"mechanism": gate_state},
    }


def packet(cid: str):
    return {
        "agent_id": "scout",
        "status": "READY",
        "candidate_ids": [cid],
        "input_refs": [f"evidence/{cid}.json"],
    }


def cycle(hour: str, c):
    return build_cycle_capture(
        active_hour_id=hour,
        source_commit=f"commit-{hour}",
        candidates=[c],
        packets=[packet(c["candidate_id"])],
    )


def captured_case():
    return cycle("H0", candidate("C1"))["cases"][0]


def test_closed_negative_resolves_immediately_and_outranks_survival():
    later = [
        cycle("H1", candidate("C1", gate_state="PASS")),
        cycle("H2", candidate("C1", gate_state="PASS")),
        cycle("H3", candidate("C1", queue_status="CLOSED_NEGATIVE", gate_state="PASS")),
    ]
    out = resolve_case(captured_case(), later)
    assert out["status"] == "RESOLVED"
    assert out["ground_truth_class"] == "DECISIVE_NEGATIVE"
    assert out["reason"] == "queue_status_closed_negative"
    assert len(out["basis_refs"]) == 1


def test_tested_negative_resolves_immediately():
    out = resolve_case(
        captured_case(),
        [cycle("H1", candidate("C1", economic_status="TESTED_NEGATIVE"))],
    )
    assert out["ground_truth_class"] == "DECISIVE_NEGATIVE"
    assert out["reason"] == "economic_status_tested_negative"


def test_required_gate_fail_is_decisive_negative():
    out = resolve_case(
        captured_case(),
        [cycle("H1", candidate("C1", gate_state="FAIL"))],
    )
    assert out["ground_truth_class"] == "DECISIVE_NEGATIVE"
    assert out["reason"] == "required_gate_fail:mechanism"


def test_survivor_requires_three_later_candidate_observations_and_progress():
    later = [
        cycle("H1", candidate("C1", gate_state="PASS")),
        cycle("H2", candidate("C1", gate_state="PASS")),
        cycle("H3", candidate("C1", gate_state="PASS")),
    ]
    out = resolve_case(captured_case(), later)
    assert out["status"] == "RESOLVED"
    assert out["ground_truth_class"] == "SURVIVOR"
    assert out["later_candidate_observations"] == 3


def test_mere_repeated_presence_without_progress_is_not_survivor():
    later = [
        cycle("H1", candidate("C1")),
        cycle("H2", candidate("C1")),
        cycle("H3", candidate("C1")),
    ]
    out = resolve_case(captured_case(), later)
    assert out["status"] == "UNRESOLVED"
    assert out["ground_truth_class"] is None


def test_waiting_for_result_is_a_progress_signal_after_horizon():
    later = [
        cycle("H1", candidate("C1", queue_status="WAITING_FOR_RESULT")),
        cycle("H2", candidate("C1", queue_status="WAITING_FOR_RESULT")),
        cycle("H3", candidate("C1", queue_status="WAITING_FOR_RESULT")),
    ]
    out = resolve_case(captured_case(), later)
    assert out["ground_truth_class"] == "SURVIVOR"


def test_cycles_without_same_candidate_do_not_count_toward_horizon():
    later = [
        cycle("H1", candidate("OTHER", gate_state="PASS")),
        cycle("H2", candidate("OTHER", gate_state="PASS")),
        cycle("H3", candidate("OTHER", gate_state="PASS")),
    ]
    out = resolve_case(captured_case(), later)
    assert out["status"] == "UNRESOLVED"
    assert out["later_candidate_observations"] == 0


def test_duplicate_later_active_hour_fails_closed():
    same = cycle("H1", candidate("C1", gate_state="PASS"))
    with pytest.raises(ValueError, match="duplicate_later_active_hour:H1"):
        resolve_case(captured_case(), [same, same])


def test_capture_hour_cannot_be_reused_as_later_observation():
    with pytest.raises(ValueError, match="later_cycle_reuses_capture_hour"):
        resolve_case(captured_case(), [cycle("H0", candidate("C1", gate_state="PASS"))])
