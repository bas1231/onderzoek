import pytest

from control.research_os_v1.candidate_view import canonicalize


def base_candidate():
    return {
        "candidate_id": "C1",
        "hypothesis": "h",
    }


def test_required_gates_override_stale_legacy_gates():
    candidate = base_candidate()
    candidate["gates"] = {
        "mechanism": "PASS",
        "execution_reality": "PASS",
    }
    candidate["required_gates"] = {
        "mechanism": "FAIL",
        "execution_reality": "FAIL",
    }
    out = canonicalize(candidate, source_commit="abc")
    assert out["required_gates"]["mechanism"] == "FAIL"
    assert out["required_gates"]["execution_reality"] == "FAIL"


def test_canonical_supporting_evidence_overrides_legacy_evidence_alias():
    candidate = base_candidate()
    candidate["evidence"] = ["legacy"]
    candidate["supporting_evidence"] = ["canonical"]
    out = canonicalize(candidate, source_commit="abc")
    assert out["supporting_evidence"] == ["canonical"]


def test_canonical_contradictory_evidence_overrides_legacy_negative_alias():
    candidate = base_candidate()
    candidate["negative_evidence"] = ["legacy-negative"]
    candidate["contradictory_evidence"] = ["canonical-negative"]
    out = canonicalize(candidate, source_commit="abc")
    assert out["contradictory_evidence"] == ["canonical-negative"]


def test_numeric_gate_state_is_rejected_not_coerced_to_pending():
    candidate = base_candidate()
    candidate["gates"] = {"mechanism": 123}
    with pytest.raises(ValueError, match="gate_status_must_be_string_or_null"):
        canonicalize(candidate, source_commit="abc")


def test_numeric_queue_status_is_rejected_not_downgraded_silently():
    candidate = base_candidate()
    candidate["queue_status"] = 123
    with pytest.raises(ValueError, match="queue_status_must_be_string_or_null"):
        canonicalize(candidate, source_commit="abc")


def test_qualified_legacy_gate_state_remains_conservative_pending():
    candidate = base_candidate()
    candidate["gates"] = {"prebuild_killer": "PASS_DISCOVERY_ONLY"}
    out = canonicalize(candidate, source_commit="abc")
    assert out["required_gates"]["prebuild_killer"] == "PENDING"
