from control.research_os_v1.red_team import build_blind_packet
from control.research_os_v1.reproducer import build_packet


def test_red_team_strips_origin_confidence_reasoning_and_evidence_polarity():
    candidate = {
        "candidate_id": "C1",
        "hypothesis": "Neutral hypothesis",
        "mechanism": "Neutral mechanism",
        "claims": [{
            "claim_id": "CL1",
            "statement": "Observable claim",
            "confidence": 0.99,
            "reasoning": "persuasive thesis prose",
            "expected_result": "win",
        }],
        "assumptions": [{
            "assumption_id": "A1",
            "statement": "Neutral assumption",
            "confidence": "high",
            "reasoning": "origin reasoning",
        }],
        "supporting_evidence": [{
            "ref": "evidence/raw/a.json",
            "upstream_source_ids": ["official:a"],
            "analysis": "this proves the thesis",
            "confidence": 0.95,
        }],
        "contradictory_evidence": [{
            "ref": "evidence/raw/b.json",
            "upstream_source_ids": ["official:b"],
            "analysis": "origin says this contradicts",
        }],
        "required_gates": {"mechanism": "PASS"},
    }
    packet = build_blind_packet(candidate)
    text = repr(packet)
    assert "persuasive thesis prose" not in text
    assert "this proves the thesis" not in text
    assert "origin says this contradicts" not in text
    assert packet["expected_result_included"] is False
    assert packet["origin_confidence_included"] is False
    assert "supporting_evidence_refs" not in packet
    assert "contradictory_evidence_refs" not in packet
    assert packet["claims"] == [{"claim_id": "CL1", "statement": "Observable claim"}]
    assert packet["evidence_refs"] == [
        {
            "ref": "evidence/raw/a.json",
            "upstream_source_ids": ["official:a"],
        },
        {
            "ref": "evidence/raw/b.json",
            "upstream_source_ids": ["official:b"],
        },
    ]
    assert packet["required_gates"] == {"mechanism": "UNKNOWN"}
    assert packet["origin_gate_states_included"] is False
    assert packet["origin_evidence_polarity_included"] is False


def test_reproducer_strips_origin_analysis_gate_states_and_evidence_polarity():
    candidate = {
        "candidate_id": "C1",
        "supporting_evidence": [{
            "evidence_ref": "raw/a.json",
            "source_id": "official-a",
            "upstream_source_ids": ["official-a"],
            "analysis": "origin worker says this is decisive",
            "expected_result": "positive",
            "confidence": 1.0,
        }],
        "contradictory_evidence": [{
            "evidence_ref": "raw/b.json",
            "source_id": "official-b",
            "upstream_source_ids": ["official-b"],
            "analysis": "origin worker called this contradictory",
        }],
        "required_gates": {
            "mechanism": "PASS",
            "market_edge": "FAIL",
        },
    }
    packet = build_packet(candidate, "Can the preregistered effect be reproduced?")
    text = repr(packet)
    assert "origin worker says this is decisive" not in text
    assert "origin worker called this contradictory" not in text
    assert "expected_result" not in text
    assert packet["origin_confidence_included"] is False
    assert "raw_evidence_refs" not in packet
    assert "contradictory_evidence_refs" not in packet
    assert packet["evidence_refs"] == [
        {
            "evidence_ref": "raw/a.json",
            "source_id": "official-a",
            "upstream_source_ids": ["official-a"],
        },
        {
            "evidence_ref": "raw/b.json",
            "source_id": "official-b",
            "upstream_source_ids": ["official-b"],
        },
    ]
    assert packet["required_gates"] == {
        "market_edge": "UNKNOWN",
        "mechanism": "UNKNOWN",
    }
    assert packet["origin_gate_states_included"] is False
    assert packet["origin_evidence_polarity_included"] is False


def test_reproducer_requires_preregistered_question():
    candidate = {"candidate_id": "C1"}
    try:
        build_packet(candidate, "")
        assert False
    except ValueError as exc:
        assert str(exc) == "preregistered_question_required"
