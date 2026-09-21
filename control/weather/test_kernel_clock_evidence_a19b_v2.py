#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control" / "weather"))

from kernel_clock_evidence_a19b_v2 import evaluate_kernel_clock_samples


def sample(offset=0.2, maxerror=2.0, esterror=1.0):
    return {
        "read_only_modes": 0,
        "time_state_name": "TIME_OK",
        "sta_unsync": False,
        "sta_clockerr": False,
        "offset_ms": offset,
        "maxerror_ms": maxerror,
        "esterror_ms": esterror,
    }


def test_pass():
    out = evaluate_kernel_clock_samples([sample() for _ in range(5)])
    assert out["evidence_clock_eligible"] is True
    assert out["decision"] == "CLOCK_EVIDENCE_PASS"
    assert out["observed"]["derived_uncertainty_ms_max"] == 2.2


def test_boundary_pass():
    out = evaluate_kernel_clock_samples([sample(offset=10.0, maxerror=90.0) for _ in range(5)])
    assert out["evidence_clock_eligible"] is True


def test_uses_larger_error_term():
    out = evaluate_kernel_clock_samples([sample(offset=1.0, maxerror=2.0, esterror=3.0) for _ in range(5)])
    assert out["observed"]["derived_uncertainty_ms_max"] == 4.0


if __name__ == "__main__":
    tests = [test_pass, test_boundary_pass, test_uses_larger_error_term]
    for test in tests:
        test()
    print(f"A19B_KERNEL_CLOCK_EVIDENCE_UNIT_TESTS_PASS {len(tests)}")
