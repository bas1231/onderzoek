import json

import pytest

from control.research_os_v1.prospective_collector import (
    build_cycle_capture,
    safe_cycle_filename,
    validate_cycle_capture,
    write_cycle_capture,
)


def candidate(cid: str):
    return {
        "candidate_id": cid,
        "hypothesis": f"hypothesis {cid}",
        "queue_status": "RUNNING",
        "priority": "P2",
        "required_gates": {"mechanism": "PENDING"},
    }


def packet(role: str, cid: str, status: str = "READY"):
    return {
        "agent_id": role,
        "status": status,
        "candidate_ids": [cid],
        "input_refs": [f"evidence/{role}/{cid}.json"],
        "point_in_time_cutoff": "2026-09-22T08:00:00Z",
    }


def test_one_case_per_candidate_per_active_hour_and_selected_task_wins():
    cycle = build_cycle_capture(
        active_hour_id="hourly-20260922T080000+0200",
        source_commit="abc123",
        candidates=[candidate("C1")],
        packets=[packet("scout", "C1"), packet("settlement", "C1")],
    )
    assert cycle["case_count"] == 1
    case = cycle["cases"][0]
    assert case["candidate_id"] == "C1"
    # Both tasks are READY/selected; the scheduler ranks the DECISIVE settlement
    # task ahead of Scout, so it is the deterministic representative.
    assert case["legacy_role"] == "settlement"
    assert case["task_shape"] == "LOW_SEQUENTIAL"
    assert case["challenger_capture"]["scheduler_decision"] == "SELECTED"
    assert case["ground_truth"] == {
        "status": "UNRESOLVED",
        "ground_truth_class": None,
        "basis_refs": [],
    }
    assert validate_cycle_capture(cycle) == []


def test_case_ids_are_deterministic_under_input_reordering():
    candidates = [candidate("C2"), candidate("C1")]
    packets = [packet("scout", "C2"), packet("settlement", "C1")]
    first = build_cycle_capture(
        active_hour_id="H1",
        source_commit="abc123",
        candidates=candidates,
        packets=packets,
    )
    second = build_cycle_capture(
        active_hour_id="H1",
        source_commit="abc123",
        candidates=list(reversed(candidates)),
        packets=list(reversed(packets)),
    )
    assert first == second
    assert [case["candidate_id"] for case in first["cases"]] == ["C1", "C2"]


def test_candidate_without_single_candidate_linked_task_is_not_a_case():
    cycle = build_cycle_capture(
        active_hour_id="H2",
        source_commit="abc123",
        candidates=[candidate("C1")],
        packets=[{"agent_id": "scout", "status": "READY", "input_refs": ["e1"]}],
    )
    assert cycle["case_count"] == 0
    assert cycle["cases"] == []
    assert validate_cycle_capture(cycle) == []


def test_duplicate_candidate_input_fails_closed():
    with pytest.raises(ValueError, match="duplicate_candidate_id:C1"):
        build_cycle_capture(
            active_hour_id="H3",
            source_commit="abc123",
            candidates=[candidate("C1"), candidate("C1")],
            packets=[packet("scout", "C1")],
        )


def test_duplicate_role_packet_fails_closed():
    with pytest.raises(ValueError, match="duplicate_agent_packet:scout"):
        build_cycle_capture(
            active_hour_id="H4",
            source_commit="abc123",
            candidates=[candidate("C1")],
            packets=[packet("scout", "C1"), packet("scout", "C1")],
        )


def test_write_is_append_only_idempotent_and_conflicting_rewrite_fails(tmp_path):
    cycle = build_cycle_capture(
        active_hour_id="H5",
        source_commit="abc123",
        candidates=[candidate("C1")],
        packets=[packet("scout", "C1")],
    )
    first = write_cycle_capture(tmp_path, cycle)
    second = write_cycle_capture(tmp_path, cycle)
    assert first["status"] == "CREATED"
    assert second["status"] == "IDEMPOTENT"

    path = tmp_path / "cycles" / safe_cycle_filename("H5")
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored == cycle

    changed = json.loads(json.dumps(cycle))
    changed["source_commit"] = "different"
    # Recompute is intentionally omitted: malformed/conflicting records must not
    # be accepted simply because the filename collides.
    with pytest.raises(ValueError, match="invalid_cycle_capture:capture_hash_mismatch"):
        write_cycle_capture(tmp_path, changed)


def test_safety_and_economic_defaults_are_hard_coded_false_no_edge():
    cycle = build_cycle_capture(
        active_hour_id="H6",
        source_commit="abc123",
        candidates=[candidate("C1")],
        packets=[packet("microstructure", "C1")],
    )
    assert cycle["live_trading"] is False
    assert cycle["paid_actions"] is False
    assert cycle["wallet_actions"] is False
    assert cycle["runtime_mutation"] is False
    assert cycle["economic_conclusion"] == "NO_PROVEN_EDGE"


def test_capture_hash_detects_tampering():
    cycle = build_cycle_capture(
        active_hour_id="H7",
        source_commit="abc123",
        candidates=[candidate("C1")],
        packets=[packet("scout", "C1")],
    )
    cycle["cases"][0]["candidate_capture"]["phase"] = "TAMPERED"
    assert "capture_hash_mismatch" in validate_cycle_capture(cycle)
