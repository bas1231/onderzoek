import pytest

from control.research_os_v1.red_team import build_blind_packet


def base_candidate():
    return {
        "candidate_id": "C1",
        "hypothesis": "Neutral testable claim",
        "claims": [],
        "assumptions": [],
        "supporting_evidence": [],
        "contradictory_evidence": [],
        "required_gates": {
            "mechanism": "PASS",
            "market_edge": "FAIL",
            "execution_reality": "PENDING",
        },
        "known_failure_patterns": [],
    }


def test_prior_gate_outcomes_are_blinded_to_unknown():
    packet = build_blind_packet(base_candidate())
    assert packet["required_gates"] == {
        "execution_reality": "UNKNOWN",
        "market_edge": "UNKNOWN",
        "mechanism": "UNKNOWN",
    }
    assert packet["origin_gate_states_included"] is False
    text = repr(packet)
    assert "'PASS'" not in text
    assert "'FAIL'" not in text
    assert "'PENDING'" not in text


def test_red_team_rejects_string_where_claim_list_required():
    candidate = base_candidate()
    candidate["claims"] = "claim text"
    with pytest.raises(ValueError, match="claims_must_be_list"):
        build_blind_packet(candidate)


def test_red_team_rejects_non_string_candidate_id():
    candidate = base_candidate()
    candidate["candidate_id"] = 123
    with pytest.raises(ValueError, match="candidate_id_required"):
        build_blind_packet(candidate)


def test_red_team_rejects_malformed_evidence_instead_of_dropping_it():
    candidate = base_candidate()
    candidate["supporting_evidence"] = [{"analysis": "origin prose only"}]
    with pytest.raises(ValueError, match="evidence_reference_has_no_provenance"):
        build_blind_packet(candidate)
