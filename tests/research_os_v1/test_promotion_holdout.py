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
