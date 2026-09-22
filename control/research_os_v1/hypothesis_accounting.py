from __future__ import annotations

from copy import deepcopy
from typing import Any

REQUIRED_FIELDS = {
    "id", "hypotheses_examined", "parameterizations_examined",
    "post_hoc_mutations", "untouched_evidence_remaining",
}
COUNT_FIELDS = (
    "hypotheses_examined",
    "parameterizations_examined",
    "post_hoc_mutations",
    "failed_variants",
    "surviving_variants",
)


def _non_negative_int(obj: dict[str, Any], key: str, *, default: int | None = None) -> int:
    if key not in obj:
        if default is None:
            raise ValueError(f"search_family_missing:{key}")
        return default
    value = obj[key]
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"search_count_must_be_integer:{key}")
    if value < 0:
        raise ValueError(f"negative_search_count:{key}")
    return value


def normalize(search_family: dict[str, Any] | None) -> dict[str, Any] | None:
    if search_family is None:
        return None
    if not isinstance(search_family, dict):
        raise ValueError("search_family_must_be_object")

    obj = deepcopy(search_family)
    missing = sorted(REQUIRED_FIELDS - set(obj))
    if missing:
        raise ValueError("search_family_missing:" + ",".join(missing))

    family_id = obj.get("id")
    if not isinstance(family_id, str) or not family_id.strip():
        raise ValueError("search_family_id_required")
    obj["id"] = family_id.strip()

    for key in COUNT_FIELDS:
        obj[key] = _non_negative_int(
            obj,
            key,
            default=0 if key in {"failed_variants", "surviving_variants"} else None,
        )

    untouched = obj.get("untouched_evidence_remaining")
    if not isinstance(untouched, bool):
        raise ValueError("untouched_evidence_remaining_must_be_boolean")

    periods = obj.get("data_periods_seen", [])
    if not isinstance(periods, list) or not all(
        isinstance(v, str) and v.strip() for v in periods
    ):
        raise ValueError("data_periods_seen_must_be_string_list")
    obj["data_periods_seen"] = [v.strip() for v in periods]

    trials = obj["hypotheses_examined"] + obj["parameterizations_examined"]
    resolved_variants = obj["failed_variants"] + obj["surviving_variants"]
    if resolved_variants > trials:
        raise ValueError("resolved_variants_exceed_recorded_search_space")
    if trials == 0 and obj["post_hoc_mutations"] > 0:
        raise ValueError("post_hoc_mutations_without_recorded_trial")

    return obj


def adaptive_search_flags(search_family: dict[str, Any] | None) -> dict[str, Any]:
    """Return deterministic evidence constraints caused by broad/adaptive search.

    This does not invent a p-value or false-discovery probability. It only
    records when discovery evidence cannot be treated like a preregistered
    first-shot hypothesis.
    """
    obj = normalize(search_family)
    if obj is None:
        return {
            "accounting_present": False,
            "adaptive_search": "UNKNOWN",
            "requires_untouched_validation": True,
            "untouched_validation_available": "UNKNOWN",
            "discovery_evidence_may_promote_directly": False,
            "promotion_blocker": "SEARCH_FAMILY_MISSING",
            "reason": "search_family_missing",
        }

    trials = obj["hypotheses_examined"] + obj["parameterizations_examined"]
    untouched = obj["untouched_evidence_remaining"]

    if trials == 0:
        return {
            "accounting_present": True,
            "adaptive_search": "UNKNOWN",
            "search_trials_recorded": 0,
            "post_hoc_mutations": obj["post_hoc_mutations"],
            "untouched_evidence_remaining": untouched,
            "untouched_validation_available": untouched,
            "requires_untouched_validation": True,
            "discovery_evidence_may_promote_directly": False,
            "promotion_blocker": "NO_SEARCH_TRIAL_RECORDED",
            "reason": "no_trials_recorded",
        }

    adaptive = obj["post_hoc_mutations"] > 0 or trials > 1
    return {
        "accounting_present": True,
        "adaptive_search": adaptive,
        "search_trials_recorded": trials,
        "post_hoc_mutations": obj["post_hoc_mutations"],
        "untouched_evidence_remaining": untouched,
        "untouched_validation_available": untouched,
        "requires_untouched_validation": adaptive,
        "discovery_evidence_may_promote_directly": (
            not adaptive and trials == 1 and untouched
        ),
        "promotion_blocker": (
            "NO_UNTOUCHED_EVIDENCE_REMAINING"
            if not untouched
            else None
        ),
        "reason": "adaptive_or_multiple_search" if adaptive else "single_preregistered_path",
    }
