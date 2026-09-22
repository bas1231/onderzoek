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


def test_search_family_keeps_methodology_but_drops_origin_prose():
    candidate = base_candidate()
    candidate["search_family"] = {
        "id": "SF-1",
        "hypotheses_examined": 3,
        "parameterizations_examined": 2,
        "post_hoc_mutations": 1,
        "failed_variants": 2,
        "surviving_variants": 1,
        "untouched_evidence_remaining": True,
        "data_periods_seen": ["development"],
        "expected_result": "this should win",
        "origin_reasoning": "persuasive prose",
    }
    packet = build_blind_packet(candidate)
    assert packet["search_family"]["id"] == "SF-1"
    assert packet["search_family"]["hypotheses_examined"] == 3
    assert "expected_result" not in packet["search_family"]
    assert "origin_reasoning" not in packet["search_family"]
    assert packet["origin_search_family_extra_fields_included"] is False


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


def test_red_team_primary_flag_alone_is_not_provenance():
    candidate = base_candidate()
    candidate["supporting_evidence"] = [{"is_primary_source": True}]
    with pytest.raises(ValueError, match="evidence_reference_has_no_provenance"):
        build_blind_packet(candidate)
