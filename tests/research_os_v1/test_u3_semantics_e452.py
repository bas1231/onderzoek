from control.jobs.review_kalshi_u3_semantics_e452 import review_artifact


def semantic(ticker: str, relation: str) -> dict:
    return {
        "ticker": ticker,
        "title": "September 2026 seasonally adjusted unemployment rate (U-3)",
        "subtitle": relation,
        "yes_sub_title": relation,
        "no_sub_title": "No",
        "rules_primary": (
            f"If the seasonally adjusted unemployment rate (U-3) reported by the "
            f"Bureau of Labor Statistics in the Employment Situation Report is {relation} "
            f"in September 2026, then the market resolves to Yes."
        ),
        "rules_secondary": (
            "Use the initial release; subsequent revisions are not used. "
            "If the report is delayed or not released, apply the same missing data rule."
        ),
        "close_time": "2026-10-02T12:00:00Z",
        "latest_expiration_time": "2027-01-01T00:00:00Z",
        "settlement_timer_seconds": 3600,
        "can_close_early": False,
    }


def artifact(*, price_fields: bool = False, exact_relation: str = "exactly 4.1%") -> dict:
    return {
        "task_id": "KALSHI-U3-SEMANTICS-E451",
        "price_fields_captured": price_fields,
        "order_book_captured": False,
        "tickers": {
            "KXU3-26SEP-T4.0": {
                "semantic": semantic("KXU3-26SEP-T4.0", "above 4.0%")
            },
            "KXU3-26SEP-T4.1": {
                "semantic": semantic("KXU3-26SEP-T4.1", "above 4.1%")
            },
            "KXECONSTATU3-26SEP-T4.1": {
                "semantic": semantic("KXECONSTATU3-26SEP-T4.1", exact_relation)
            },
        },
    }


def test_missing_artifact_shape_fails_closed():
    review = review_artifact({"task_id": "KALSHI-U3-SEMANTICS-E451"}, grid_note_present=True)
    assert review["mechanism"] == "BLOCKED_SEMANTICS"
    assert review["price_comparison_authorized"] is False
    assert review["summary"]["failures"] >= 1


def test_price_contamination_blocks_semantic_review():
    review = review_artifact(artifact(price_fields=True), grid_note_present=True)
    assert review["checks"]["semantic_only_capture"]["status"] == "FAIL"
    assert review["mechanism"] == "BLOCKED_SEMANTICS"
    assert review["price_comparison_authorized"] is False


def test_exact_market_must_explicitly_encode_equality():
    review = review_artifact(artifact(exact_relation="above 4.1%"), grid_note_present=True)
    check = review["checks"]["markets"]["KXECONSTATU3-26SEP-T4.1"]["relation"]
    assert check["status"] == "FAIL"
    assert review["mechanism"] == "BLOCKED_SEMANTICS"


def test_explicit_policy_language_still_does_not_auto_promote():
    review = review_artifact(artifact(), grid_note_present=True)
    assert review["summary"]["failures"] == 0
    assert review["summary"]["unknowns"] == 0
    assert review["summary"]["supported_needing_manual_alignment"] >= 1
    assert review["mechanism"] == "BLOCKED_SEMANTICS"
    assert review["price_comparison_authorized"] is False
    assert review["economic_conclusion"] == "NO_PROVEN_EDGE"
