#!/usr/bin/env python3
"""A19C: read-only clock-evidence diagnostic for prospective LDM latency work.

This diagnostic never installs, enables, or changes time-sync software.  A
successful diagnostic may legitimately end at BLOCKED_CLOCK_EVIDENCE.  That is
an external/system readiness gate, not a software failure and not evidence of
market edge.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

ROOT = Path.cwd()
WEATHER = ROOT / "control" / "weather"
sys.path.insert(0, str(WEATHER))

import madis_ldm_queue_native_a19b_v2 as q  # noqa: E402

MAX_UNCERTAINTY_MS = 100.0


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def classify_clock_evidence(clock: dict[str, Any]) -> dict[str, Any]:
    """Independently fail-close the clock evidence produced by A19B-v2."""
    source = clock.get("clock_source")
    offset = _finite_number(clock.get("clock_offset_ms"))
    uncertainty = _finite_number(clock.get("clock_uncertainty_ms"))
    upstream_eligible = clock.get("evidence_clock_eligible") is True

    reasons: list[str] = []
    if not isinstance(source, str) or not source.strip():
        reasons.append("MISSING_CLOCK_SOURCE")
    if offset is None:
        reasons.append("MISSING_OR_NONFINITE_CLOCK_OFFSET")
    if uncertainty is None:
        reasons.append("MISSING_OR_NONFINITE_CLOCK_UNCERTAINTY")
    elif uncertainty < 0:
        reasons.append("NEGATIVE_CLOCK_UNCERTAINTY")
    elif uncertainty > MAX_UNCERTAINTY_MS:
        reasons.append("CLOCK_UNCERTAINTY_ABOVE_GATE")
    if not upstream_eligible:
        reasons.append("UPSTREAM_CLOCK_GATE_NOT_ELIGIBLE")

    eligible = not reasons
    return {
        "clock_evidence_eligible": eligible,
        "clock_source": source if isinstance(source, str) else None,
        "clock_offset_ms": offset,
        "clock_uncertainty_ms": uncertainty,
        "max_clock_uncertainty_ms": MAX_UNCERTAINTY_MS,
        "reasons": reasons,
    }


def _run_readonly(*args: str, timeout: int = 5) -> dict[str, Any]:
    try:
        cp = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)
        return {
            "command": list(args),
            "returncode": cp.returncode,
            "stdout": cp.stdout[-6000:],
            "stderr": cp.stderr[-3000:],
        }
    except Exception as exc:
        return {
            "command": list(args),
            "returncode": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def readonly_clock_inventory() -> dict[str, Any]:
    commands = {
        name: shutil.which(name)
        for name in ("chronyc", "timedatectl", "ntptime", "adjtimex")
    }
    evidence: dict[str, Any] = {"commands": commands}

    if commands["timedatectl"]:
        evidence["timedatectl_ntp_synchronized"] = _run_readonly(
            "timedatectl", "show", "-p", "NTPSynchronized", "--value"
        )
        evidence["timedatectl_timesync"] = _run_readonly(
            "timedatectl", "show-timesync", "--all"
        )
    if commands["chronyc"]:
        evidence["chronyc_tracking"] = _run_readonly("chronyc", "tracking", "-n")
    if commands["ntptime"]:
        evidence["ntptime"] = _run_readonly("ntptime")
    if commands["adjtimex"]:
        evidence["adjtimex_print"] = _run_readonly("adjtimex", "--print")

    return evidence


def build_report() -> dict[str, Any]:
    clock = q.clock_health()
    classification = classify_clock_evidence(clock)
    eligible = classification["clock_evidence_eligible"] is True

    return {
        "task": "WEATHER-A19C-CLOCK-EVIDENCE-DIAGNOSTIC",
        "status": "COMPLETED_DIAGNOSTIC",
        "clock_gate_status": "PASS_CLOCK_EVIDENCE" if eligible else "BLOCKED_CLOCK_EVIDENCE",
        "next_gate": (
            "A19C_CLOCK_EVIDENCE_SATISFIED_ADVANCE_TO_REAL_LDM_RUNTIME"
            if eligible
            else "BLOCKED_CLOCK_EVIDENCE"
        ),
        "clock_health": clock,
        "clock_classification": classification,
        "readonly_inventory": readonly_clock_inventory(),
        "required_for_prospective_latency_evidence": [
            "nonempty clock_source",
            "finite clock_offset_ms",
            "finite nonnegative clock_uncertainty_ms <= 100",
            "A19B evidence_clock_eligible == true",
        ],
        "mutation_performed": False,
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
        "economic_conclusion": "NO_PROVEN_EDGE",
    }


if __name__ == "__main__":
    print(json.dumps(build_report(), indent=2, sort_keys=True))
    raise SystemExit(0)
