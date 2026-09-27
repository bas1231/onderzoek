import pytest

from control.research_os_v1.hypothesis_accounting import adaptive_search_flags, normalize
from control.research_os_v1.discovery_coverage import summarize


def test_string_false_is_not_accepted_as_boolean_holdout_state():
    with pytest.raises(ValueError, match="untouched_evidence_remaining_must_be_boolean"):
        normalize({
            "id": "F1",
            "hypotheses_examined": 1,
            "parameterizations_examined": 0,
            "post_hoc_mutations": 0,
            "untouched_evidence_remaining": "false",
        })


def test_boolean_is_not_accepted_as_integer_search_count():
    with pytest.raises(ValueError, match="search_count_must_be_integer:hypotheses_examined"):
        normalize({
            "id": "F1",
            "hypotheses_examined": True,
            "parameterizations_examined": 0,
            "post_hoc_mutations": 0,
            "untouched_evidence_remaining": True,
        })


def test_missing_accounting_never_allows_direct_promotion():
    flags = adaptive_search_flags(None)
    assert flags["accounting_present"] is False
    assert flags["requires_untouched_validation"] is True
    assert flags["discovery_evidence_may_promote_directly"] is False
    assert flags["promotion_blocker"] == "SEARCH_FAMILY_MISSING"


def test_zero_recorded_trials_are_unknown_and_block_direct_use():
    flags = adaptive_search_flags({
        "id": "F0",
        "hypotheses_examined": 0,
        "parameterizations_examined": 0,
        "post_hoc_mutations": 0,
        "untouched_evidence_remaining": True,
    })
    assert flags["adaptive_search"] == "UNKNOWN"
    assert flags["search_trials_recorded"] == 0
    assert flags["requires_untouched_validation"] is True
    assert flags["discovery_evidence_may_promote_directly"] is False
    assert flags["promotion_blocker"] == "NO_SEARCH_TRIAL_RECORDED"
    assert flags["reason"] == "no_trials_recorded"


def test_post_hoc_mutation_without_recorded_trial_is_invalid_accounting():
    with pytest.raises(ValueError, match="post_hoc_mutations_without_recorded_trial"):
        normalize({
            "id": "F0-MUTATED",
            "hypotheses_examined": 0,
            "parameterizations_examined": 0,
            "post_hoc_mutations": 1,
            "untouched_evidence_remaining": True,
        })


def test_resolved_variants_may_not_exceed_recorded_search_space():
    with pytest.raises(ValueError, match="resolved_variants_exceed_recorded_search_space"):
        normalize({
            "id": "F-BAD-COUNTS",
            "hypotheses_examined": 1,
            "parameterizations_examined": 1,
            "post_hoc_mutations": 0,
            "failed_variants": 2,
            "surviving_variants": 1,
            "untouched_evidence_remaining": True,
        })


def test_single_recorded_path_without_untouched_evidence_cannot_promote_directly():
    flags = adaptive_search_flags({
        "id": "F1-NO-HOLDOUT",
        "hypotheses_examined": 1,
        "parameterizations_examined": 0,
        "post_hoc_mutations": 0,
        "untouched_evidence_remaining": False,
    })
    assert flags["adaptive_search"] is False
    assert flags["discovery_evidence_may_promote_directly"] is False
    assert flags["promotion_blocker"] == "NO_UNTOUCHED_EVIDENCE_REMAINING"


def test_adaptive_search_without_untouched_evidence_exposes_blocker():
    flags = adaptive_search_flags({
        "id": "F1",
        "hypotheses_examined": 4,
        "parameterizations_examined": 2,
        "post_hoc_mutations": 1,
        "untouched_evidence_remaining": False,
    })
    assert flags["adaptive_search"] is True
    assert flags["untouched_validation_available"] is False
    assert flags["promotion_blocker"] == "NO_UNTOUCHED_EVIDENCE_REMAINING"


def test_zero_discovery_denominators_are_unknown_not_zero():
    out = summarize([], [], [], [])
    assert out["duplicate_cross_scout_ratio"] is None
    assert out["primary_source_ratio"] is None
    assert out["zero_denominator_metrics_are_unknown"] is True


def test_same_content_hash_on_different_sources_is_cross_scout_duplicate():
    p = [{
        "source_id": "official-url-a",
        "document_sha256": "ABC123",
        "source_family": "official_rules_contracts",
        "retrieval_succeeded": True,
    }]
    r = [{
        "source_id": "mirror-url-b",
        "document_sha256": "abc123",
        "source_family": "community_discussion_weak_signals",
        "retrieval_succeeded": True,
    }]
    out = summarize(p, r, ["official_rules_contracts"], ["official_rules_contracts"])
    assert out["identified_document_keys"] == 1
    assert out["duplicate_cross_scout_keys"] == 1
    assert out["duplicate_cross_scout_ratio"] == 1.0


def test_attempted_but_failed_family_is_not_retrieval_complete():
    p = [{
        "source_id": "official-url-a",
        "source_family": "official_rules_contracts",
        "source_state": "FAILED",
        "retrieval_succeeded": False,
    }]
    out = summarize(
        p,
        [],
        ["official_rules_contracts"],
        ["official_rules_contracts"],
    )
    assert out["coverage_attempt_complete"] is True
    assert out["coverage_retrieval_complete"] is False
    assert out["coverage_complete"] is False
    assert out["retrieval_coverage_gaps"] == ["official_rules_contracts"]


def test_missing_retrieval_status_is_unknown_not_success():
    p = [{
        "source_id": "official-url-a",
        "source_family": "official_rules_contracts",
    }]
    out = summarize(
        p,
        [],
        ["official_rules_contracts"],
        ["official_rules_contracts"],
    )
    assert out["successful_retrieval_items"] == 0
    assert out["unknown_retrieval_status_items"] == 1
    assert out["coverage_retrieval_complete"] is False
    assert out["missing_retrieval_status_counts_as_success"] is False


def test_source_family_matching_is_case_insensitive():
    p = [{
        "source_id": "official-url-a",
        "source_family": "Official_Rules_Contracts",
        "retrieval_succeeded": True,
    }]
    out = summarize(
        p,
        [],
        ["OFFICIAL_RULES_CONTRACTS"],
        ["official_rules_contracts"],
    )
    assert out["coverage_attempt_complete"] is True
    assert out["coverage_retrieval_complete"] is True
    assert out["successful_source_families"] == ["official_rules_contracts"]


def test_unidentified_relevant_items_do_not_inflate_unique_document_count():
    p = [{
        "source_family": "official_rules_contracts",
        "retrieval_succeeded": True,
        "relevant": True,
        "changed_or_new": True,
    }]
    out = summarize(p, [], ["official_rules_contracts"], ["official_rules_contracts"])
    assert out["relevant_unidentified_items"] == 1
    assert out["unique_relevant_items_reported"] == 0
    assert out["changed_or_new_unidentified_items"] == 1
    assert out["changed_or_new_documents"] == 0
    assert out["unidentified_items_count_as_proven_unique_documents"] is False


def test_primary_source_ratio_uses_successful_retrievals_only():
    p = [
        {
            "source_id": "good-primary",
            "source_family": "official_rules_contracts",
            "source_authority": "OFFICIAL_PRIMARY",
            "retrieval_succeeded": True,
        },
        {
            "source_id": "failed-secondary",
            "source_family": "code",
            "retrieval_succeeded": False,
        },
    ]
    out = summarize(p, [], ["official_rules_contracts", "code"], ["official_rules_contracts"])
    assert out["successful_retrieval_items"] == 1
    assert out["primary_source_ratio"] == 1.0
