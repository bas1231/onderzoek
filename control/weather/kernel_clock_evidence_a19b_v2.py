#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

CLOCK_MAX_UNCERTAINTY_MS = 100.0
REQUIRED_SAMPLES = 5


def _num(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def evaluate_kernel_clock_samples(
    samples: list[dict[str, Any]],
    *,
    max_uncertainty_ms: float = CLOCK_MAX_UNCERTAINTY_MS,
) -> dict[str, Any]:
    """Fail-closed decision for read-only Linux adjtimex() evidence.

    This is a project-local evidence gate, not a Linux/chrony formal uncertainty
    claim. For each sample we derive a conservative bound:

        abs(offset_ms) + max(maxerror_ms, esterror_ms)

    Eligibility requires exactly the expected evidence quality across at least
    REQUIRED_SAMPLES independent probe observations.
    """
    reasons: list[str] = []
    normalized: list[dict[str, Any]] = []

    if not isinstance(samples, list) or len(samples) < REQUIRED_SAMPLES:
        reasons.append("INSUFFICIENT_KERNEL_CLOCK_SAMPLES")

    for index, sample in enumerate(samples if isinstance(samples, list) else []):
        if not isinstance(sample, dict):
            reasons.append(f"SAMPLE_{index}_NOT_OBJECT")
            continue

        state = sample.get("time_state_name")
        unsync = sample.get("sta_unsync")
        clockerr = sample.get("sta_clockerr")
        offset = _num(sample.get("offset_ms"))
        maxerror = _num(sample.get("maxerror_ms"))
        esterror = _num(sample.get("esterror_ms"))
        read_only_modes = sample.get("read_only_modes")

        if read_only_modes != 0:
            reasons.append(f"SAMPLE_{index}_NOT_READ_ONLY")
        if state != "TIME_OK":
            reasons.append(f"SAMPLE_{index}_TIME_STATE_{state}")
        if unsync is not False:
            reasons.append(f"SAMPLE_{index}_STA_UNSYNC")
        if clockerr is not False:
            reasons.append(f"SAMPLE_{index}_STA_CLOCKERR")
        if offset is None or maxerror is None or esterror is None:
            reasons.append(f"SAMPLE_{index}_MISSING_NUMERIC_CLOCK_FIELDS")
            continue
        if maxerror < 0 or esterror < 0:
            reasons.append(f"SAMPLE_{index}_NEGATIVE_ERROR_FIELD")
            continue

        uncertainty = abs(offset) + max(maxerror, esterror)
        if uncertainty > max_uncertainty_ms:
            reasons.append(f"SAMPLE_{index}_UNCERTAINTY_ABOVE_LIMIT")

        normalized.append({
            "sample_index": index,
            "offset_ms": offset,
            "maxerror_ms": maxerror,
            "esterror_ms": esterror,
            "derived_uncertainty_ms": uncertainty,
            "time_state_name": state,
            "sta_unsync": unsync,
            "sta_clockerr": clockerr,
            "read_only_modes": read_only_modes,
        })

    eligible = bool(
        len(samples) >= REQUIRED_SAMPLES
        and len(normalized) == len(samples)
        and not reasons
    )

    offsets = [row["offset_ms"] for row in normalized]
    uncertainties = [row["derived_uncertainty_ms"] for row in normalized]

    return {
        "schema": "A19B_KERNEL_CLOCK_EVIDENCE_V1",
        "evidence_clock_eligible": eligible,
        "decision": "CLOCK_EVIDENCE_PASS" if eligible else "CLOCK_EVIDENCE_BLOCKED",
        "reasons": sorted(set(reasons)),
        "sample_count": len(samples) if isinstance(samples, list) else 0,
        "required_sample_count": REQUIRED_SAMPLES,
        "max_uncertainty_limit_ms": max_uncertainty_ms,
        "uncertainty_semantics": "project-local conservative gate = abs(kernel_offset_ms)+max(kernel_maxerror_ms,kernel_esterror_ms)",
        "normalized_samples": normalized,
        "observed": {
            "offset_ms_min": min(offsets) if offsets else None,
            "offset_ms_max": max(offsets) if offsets else None,
            "derived_uncertainty_ms_max": max(uncertainties) if uncertainties else None,
        },
    }
