import pytest

from control.research_os_v1.resurrection import evaluate


def killed_candidate():
    return {
        "candidate_id": "C1",
        "queue_status": "CLOSED_NEGATIVE",
        "economic_status": "TESTED_NEGATIVE",
        "phase": "VALIDATION",
        "resurrection_conditions": ["reward_active"],
        "required_gates": {
            "source_provenance": "PASS",
            "mechanism": "PASS",
        },
        "blockers": [],
    }


def test_changed_conditions_must_be_list_not_string_iterable():
    with pytest.raises(
        ValueError,
        match="changed_conditions_must_be_list_of_nonempty_strings",
    ):
        evaluate(killed_candidate(), "reward_active", "2026-09-22T00:00:00Z")


def test_resurrection_conditions_must_be_list_not_string_iterable():
    candidate = killed_candidate()
    candidate["resurrection_conditions"] = "reward_active"
    with pytest.raises(
        ValueError,
        match="resurrection_conditions_must_be_list_of_nonempty_strings",
    ):
        evaluate(candidate, ["reward_active"], "2026-09-22T00:00:00Z")


def test_condition_match_is_exact_not_substring_or_character_match():
    result = evaluate(
        killed_candidate(),
        ["reward"],
        "2026-09-22T00:00:00Z",
    )
    assert result["resurrected"] is False
    assert result["matched_conditions"] == []


def test_resurrection_resets_every_existing_gate_and_preserves_old_snapshot():
    result = evaluate(
        killed_candidate(),
        ["reward_active"],
        "2026-09-22T00:00:00Z",
    )
    assert result["resurrected"] is True
    assert set(result["candidate"]["required_gates"].values()) == {"PENDING"}
    old = result["candidate"]["resurrection_history"][-1]
    assert old["required_gates"]["mechanism"] == "PASS"
    assert result["old_gate_passes_inherited"] is False


def test_corrupt_history_is_rejected_not_flattened():
    candidate = killed_candidate()
    candidate["resurrection_history"] = "old-history"
    with pytest.raises(ValueError, match="resurrection_history_must_be_list_of_objects"):
        evaluate(candidate, ["reward_active"], "2026-09-22T00:00:00Z")
