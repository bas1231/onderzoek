from __future__ import annotations

from copy import deepcopy
from typing import Any

REQUIRED_FIELDS = {
    "id", "hypotheses_examined", "parameterizations_examined",
    "post_hoc_mutations", "untouched_evidence_remaining",
}


def normalize(search_family: dict[str, Any] | None) -> dict[str, Any] | None:
    if search_family is None:
        return None
    obj = deepcopy(search_family)
    missing = sorted(REQUIRED_FIELDS - set(obj))
    if missing:
        raise ValueError("search_family_missing:" + ",".join(missing))
    for key in ("hypotheses_examined", "parameterizations_examined", "post_hoc_mutations"):
        value = int(obj[key])
        if value < 0:
            raise ValueError(f"negative_search_count:{key}")
        obj[key] = value
    obj["untouched_evidence_remaining"] = bool(obj["untouched_evidence_remaining"])
    obj.setdefault("failed_variants", 0)
    obj.setdefault("surviving_variants", 0)
    obj.setdefault("data_periods_seen", [])
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
            "reason": "search_family_missing",
        }

    trials = obj["hypotheses_examined"] + obj["parameterizations_examined"]
    adaptive = obj["post_hoc_mutations"] > 0 or trials > 1
    return {
        "accounting_present": True,
        "adaptive_search": adaptive,
        "search_trials_recorded": trials,
        "post_hoc_mutations": obj["post_hoc_mutations"],
        "untouched_evidence_remaining": obj["untouched_evidence_remaining"],
        "requires_untouched_validation": adaptive,
        "discovery_evidence_may_promote_directly": not adaptive,
        "reason": "adaptive_or_multiple_search" if adaptive else "single_preregistered_path",
    }
