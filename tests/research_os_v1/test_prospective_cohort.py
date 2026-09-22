import json

import pytest

from control.research_os_v1.prospective_collector import build_cycle_capture
from control.research_os_v1.prospective_cohort import build_cohort_status, write_cohort_lock


def candidate(cid, *, queue_status="RUNNING", gate="PENDING", economic_status="NO_PROVEN_EDGE"):
    return {
        "candidate_id": cid,
        "hypothesis": f"hypothesis {cid}",
        "queue_status": queue_status,
        "economic_status": economic_status,
        "priority": "P2",
        "required_gates": {"mechanism": gate},
    }


def packet(role, cid):
    return {
        "agent_id": role,
        "status": "READY",
        "candidate_ids": [cid],
        "input_refs": [f"evidence/{role}/{cid}.json"],
    }


def hour(index):
    return f"hourly-20260922T{index:02d}0000+0200"


def cycle(index, *, neg_status="RUNNING", neg_gate="PENDING", surv_gate="PASS"):
    return build_cycle_capture(
        active_hour_id=hour(index),
        source_commit=f"commit-{index}",
        candidates=[
            candidate("CNEG", queue_status=neg_status, gate=neg_gate),
            candidate("CSURV", gate=surv_gate),
        ],
        packets=[
            packet("scout", "CNEG"),
            packet("settlement", "CSURV"),
        ],
    )


def test_before_raw_minimum_status_is_collecting():
    status = build_cohort_status([cycle(i) for i in range(9)])
    assert status["status"] == "COLLECTING"
    assert status["cohort_frozen"] is False
    assert status["candidate_events_observed"] == 18
    assert status["active_hour_cycles_observed"] == 9


def test_cutoff_freezes_first_cycle_where_raw_minimums_met():
    cycles = [cycle(i) for i in range(10)]
    # Later cycles exist, but must not enlarge the cohort after H09 cutoff.
    cycles += [cycle(10), cycle(11), cycle(12)]
    status = build_cohort_status(cycles)
    assert status["cohort_frozen"] is True
    assert status["cutoff_active_hour_id"] == hour(9)
    assert status["cohort_cycle_count"] == 10
    assert status["cohort_case_count"] == 20
    assert all(hour(10) not in cid for cid in status["cohort_case_ids"])


def test_resolution_only_cycles_can_resolve_frozen_cohort_ready():
    cycles = [cycle(i) for i in range(10)]
    # First resolution-only cycle makes the negative class decisive.
    cycles.append(cycle(10, neg_status="CLOSED_NEGATIVE"))
    # Three post-cutoff observations allow even H09 survivor cases to resolve.
    cycles.append(cycle(11, neg_status="CLOSED_NEGATIVE"))
    cycles.append(cycle(12, neg_status="CLOSED_NEGATIVE"))
    status = build_cohort_status(cycles)
    assert status["status"] == "READY_FOR_PAIRED_OBSERVATIONS"
    assert status["replacement_benchmark_ready"] is True
    assert status["unresolved_cases"] == 0
    assert status["resolved_survivors"] == 10
    assert status["resolved_decisive_negatives"] == 10


def test_unresolved_cases_block_after_cutoff():
    status = build_cohort_status([cycle(i) for i in range(10)])
    assert status["status"] == "RESOLVING"
    assert status["replacement_benchmark_ready"] is False
    assert status["unresolved_cases"] > 0


def test_missing_class_balance_does_not_extend_cohort_post_hoc():
    cycles = [
        build_cycle_capture(
            active_hour_id=hour(i),
            source_commit=f"commit-{i}",
            candidates=[candidate("C1", gate="PASS"), candidate("C2", gate="PASS")],
            packets=[packet("scout", "C1"), packet("settlement", "C2")],
        )
        for i in range(13)
    ]
    status = build_cohort_status(cycles)
    assert status["status"] == "INSUFFICIENT_CLASS_BALANCE"
    assert status["cohort_case_count"] == 20
    assert status["resolved_survivors"] == 20
    assert status["resolved_decisive_negatives"] == 0
    assert status["replacement_benchmark_ready"] is False


def test_cohort_lock_is_immutable_and_idempotent(tmp_path):
    cycles = [cycle(i) for i in range(10)] + [
        cycle(10, neg_status="CLOSED_NEGATIVE"),
        cycle(11, neg_status="CLOSED_NEGATIVE"),
        cycle(12, neg_status="CLOSED_NEGATIVE"),
    ]
    status = build_cohort_status(cycles)
    first = write_cohort_lock(tmp_path, status)
    second = write_cohort_lock(tmp_path, status)
    assert first["status"] == "CREATED"
    assert second["status"] == "IDEMPOTENT"

    path = tmp_path / "cohort_lock.json"
    lock = json.loads(path.read_text(encoding="utf-8"))
    lock["cohort_case_ids"] = lock["cohort_case_ids"][:-1]
    path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="cohort_lock_conflict"):
        write_cohort_lock(tmp_path, status)


def test_invalid_active_hour_format_fails_closed():
    bad = build_cycle_capture(
        active_hour_id="not-a-real-active-hour",
        source_commit="abc",
        candidates=[candidate("C1", gate="PASS")],
        packets=[packet("scout", "C1")],
    )
    with pytest.raises(ValueError, match="invalid_active_hour_id"):
        build_cohort_status([bad])
