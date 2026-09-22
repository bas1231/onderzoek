import pytest

from control.research_os_v1.candidate_view import canonicalize


def test_empty_legacy_gates_do_not_erase_required_gates():
    src = {
        "candidate_id": "C-MIXED",
        "hypothesis": "h",
        "required_gates": {
            "mechanism": "PASS",
            "execution_reality": "FAIL",
        },
        "gates": {},
    }
    out = canonicalize(src, source_commit="abc")
    assert out["required_gates"]["mechanism"] == "PASS"
    assert out["required_gates"]["execution_reality"] == "FAIL"


def test_conflicting_legacy_and_canonical_gate_state_fails_closed():
    src = {
        "candidate_id": "C-MERGE",
        "hypothesis": "h",
        "required_gates": {
            "mechanism": "PASS",
            "execution_reality": "PASS",
        },
        "gates": {"execution_reality": "FAIL"},
    }
    with pytest.raises(ValueError, match="conflicting_gate_state:execution_reality"):
        canonicalize(src, source_commit="abc")


def test_equivalent_gate_aliases_do_not_create_false_conflict():
    src = {
        "candidate_id": "C-ALIAS",
        "hypothesis": "h",
        "required_gates": {"execution_reality": "FAIL"},
        "gates": {"execution_reality": "FAILED"},
    }
    out = canonicalize(src, source_commit="abc")
    assert out["required_gates"]["execution_reality"] == "FAIL"


def test_recanonicalizing_non_proven_positive_state_is_idempotent():
    first = canonicalize(
        {
            "candidate_id": "C-POS",
            "hypothesis": "h",
            "economic_status": "RESEARCH_POSITIVE",
            "required_gates": {"mechanism": "PASS"},
        },
        source_commit="first",
    )
    second = canonicalize(first, source_commit="second")
    assert first["economic_status"] == "RESEARCH_POSITIVE"
    assert second["economic_status"] == "RESEARCH_POSITIVE"
    assert second["required_gates"] == first["required_gates"]


def test_negative_state_outranks_stale_optimistic_decision():
    out = canonicalize(
        {
            "candidate_id": "C-CONFLICT",
            "hypothesis": "h",
            "decision": "RESEARCH_POSITIVE",
            "economic_status": "TESTED_NEGATIVE",
            "required_gates": {"mechanism": "FAIL"},
        },
        source_commit="abc",
    )
    assert out["economic_status"] == "TESTED_NEGATIVE"
    assert out["required_gates"]["mechanism"] == "FAIL"


def test_unsupported_positive_state_downgrades_to_no_proven_edge():
    out = canonicalize(
        {
            "candidate_id": "C-UNSAFE",
            "hypothesis": "h",
            "economic_status": "PROVEN_EDGE_CANDIDATE",
            "required_gates": {},
        },
        source_commit="abc",
    )
    assert out["economic_status"] == "NO_PROVEN_EDGE"


def test_unknown_queue_status_is_rejected_not_silently_rewritten():
    with pytest.raises(ValueError, match="unknown_queue_status:MYSTERY"):
        canonicalize(
            {
                "candidate_id": "C-Q",
                "hypothesis": "h",
                "queue_status": "mystery",
            },
            source_commit="abc",
        )


def test_unknown_priority_is_rejected_not_silently_rewritten():
    with pytest.raises(ValueError, match="unknown_priority:P9"):
        canonicalize(
            {
                "candidate_id": "C-P",
                "hypothesis": "h",
                "priority": "P9",
            },
            source_commit="abc",
        )


def test_legacy_partial_pass_labels_never_upgrade_to_full_pass():
    out = canonicalize(
        {
            "candidate_id": "C-LEGACY-PARTIAL",
            "hypothesis": "h",
            "gates": {
                "point_in_time": "PENDING_PROSPECTIVE",
                "prebuild_killer": "PASS_DISCOVERY_ONLY",
                "development": "DISCOVERY_COMPLETE",
            },
        },
        source_commit="abc",
    )
    assert out["required_gates"]["point_in_time"] == "PENDING"
    assert out["required_gates"]["prebuild_killer"] == "PENDING"
    assert out["required_gates"]["development"] == "PENDING"
