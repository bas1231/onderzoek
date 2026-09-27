from control.research_os_v1.promotion import evaluate


ALL_GATES = [
    "source_provenance",
    "point_in_time",
    "mechanism",
    "signal_edge",
    "market_edge",
    "execution_reality",
    "prebuild_killer",
    "chief_falsifier",
    "validation",
    "holdout",
    "independent_reproduction",
    "shadow",
]


def candidate_with_all_passes():
    return {"required_gates": {gate: "PASS" for gate in ALL_GATES}}


def test_missing_holdout_blocks_promotion():
    candidate = candidate_with_all_passes()
    candidate["required_gates"].pop("holdout")
    result = evaluate(candidate)
    assert result["eligible"] is False
    assert result["status"] == "INCOMPLETE_GATES"
    assert "holdout" in result["pending_gates"]
    assert result["live_trading_authorized"] is False


def test_failed_holdout_blocks_promotion():
    candidate = candidate_with_all_passes()
    candidate["required_gates"]["holdout"] = "FAIL"
    result = evaluate(candidate)
    assert result["eligible"] is False
    assert "holdout" in result["failed_gates"]
    assert result["live_trading_authorized"] is False


def test_full_gate_set_can_only_be_promotion_candidate_not_live_authorization():
    result = evaluate(candidate_with_all_passes())
    assert result["eligible"] is True
    assert result["status"] == "PROMOTION_CANDIDATE"
    assert result["live_trading_authorized"] is False


def test_future_failed_required_gate_cannot_be_ignored():
    candidate = candidate_with_all_passes()
    candidate["required_gates"]["future_execution_integrity_gate"] = "FAIL"
    result = evaluate(candidate)
    assert result["eligible"] is False
    assert result["status"] == "BLOCKED_GATE"
    assert "future_execution_integrity_gate" in result["failed_gates"]


def test_future_pending_required_gate_cannot_be_ignored():
    candidate = candidate_with_all_passes()
    candidate["required_gates"]["future_execution_integrity_gate"] = "PENDING"
    result = evaluate(candidate)
    assert result["eligible"] is False
    assert "future_execution_integrity_gate" in result["pending_gates"]


def test_unknown_gate_state_is_rejected_not_coerced():
    candidate = candidate_with_all_passes()
    candidate["required_gates"]["mechanism"] = "looks_good"
    try:
        evaluate(candidate)
        assert False
    except ValueError as exc:
        assert "invalid_gate_state" in str(exc)


def test_signal_required_flag_must_be_boolean():
    try:
        evaluate(candidate_with_all_passes(), signal_required="false")
        assert False
    except ValueError as exc:
        assert str(exc) == "signal_required_must_be_boolean"
