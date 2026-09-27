from control.research_os_v1.candidate_view import canonicalize
from control.research_os_v1.resurrection import evaluate


def test_resurrection_resets_legacy_and_canonical_gate_union():
    candidate = {
        "candidate_id": "C1",
        "hypothesis": "h",
        "queue_status": "CLOSED_NEGATIVE",
        "economic_status": "TESTED_NEGATIVE",
        "resurrection_conditions": ["reward_active"],
        "gates": {
            "mechanism": "PASS",
            "point_in_time": "PASS",
        },
        "required_gates": {
            "execution_reality": "PASS",
        },
    }
    out = evaluate(candidate, ["reward_active"], "2026-09-22T05:00:00Z")
    assert out["resurrected"] is True
    assert out["candidate"]["required_gates"] == {
        "execution_reality": "PENDING",
        "mechanism": "PENDING",
        "point_in_time": "PENDING",
    }
    assert out["candidate"]["gates"] == out["candidate"]["required_gates"]
    history = out["candidate"]["resurrection_history"][0]
    assert history["legacy_gates"]["mechanism"] == "PASS"
    assert history["required_gates"]["execution_reality"] == "PASS"


def test_resurrected_candidate_recanonicalizes_without_old_pass_leak():
    candidate = {
        "candidate_id": "C2",
        "hypothesis": "h",
        "queue_status": "CLOSED_NEGATIVE",
        "economic_status": "TESTED_NEGATIVE",
        "resurrection_conditions": ["fee_change"],
        "gates": {"mechanism": "PASS"},
    }
    resurrected = evaluate(candidate, ["fee_change"], "2026-09-22T05:00:00Z")["candidate"]
    canonical = canonicalize(resurrected, source_commit="abc")
    assert canonical["economic_status"] == "NO_PROVEN_EDGE"
    assert canonical["queue_status"] == "NEEDS_REVISION"
    assert canonical["required_gates"]["mechanism"] == "PENDING"


def test_legacy_resume_condition_is_supported_but_not_inherited_as_validation():
    candidate = {
        "candidate_id": "C3",
        "hypothesis": "h",
        "queue_status": "CLOSED_NEGATIVE",
        "economic_status": "TESTED_NEGATIVE",
        "resume_condition": "rules_changed",
        "gates": {"mechanism": "PASS"},
    }
    out = evaluate(candidate, ["rules_changed"], "2026-09-22T05:00:00Z")
    assert out["resurrected"] is True
    assert out["candidate"]["resurrection_conditions"] == ["rules_changed"]
    assert out["candidate"]["gates"]["mechanism"] == "PENDING"
    assert out["old_gate_passes_inherited"] is False
