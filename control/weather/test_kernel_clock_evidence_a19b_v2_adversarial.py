#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control" / "weather"))
from kernel_clock_evidence_a19b_v2 import evaluate_kernel_clock_samples


def base():
    return {
        "read_only_modes": 0,
        "time_state_name": "TIME_OK",
        "sta_unsync": False,
        "sta_clockerr": False,
        "offset_ms": 0.1,
        "maxerror_ms": 1.0,
        "esterror_ms": 1.0,
    }


def run_case(mutator):
    rows=[base() for _ in range(5)]
    mutator(rows)
    out=evaluate_kernel_clock_samples(rows)
    assert out["evidence_clock_eligible"] is False
    assert out["decision"] == "CLOCK_EVIDENCE_BLOCKED"


def test_unsync(): run_case(lambda r: r[0].__setitem__("sta_unsync", True))
def test_clockerr(): run_case(lambda r: r[0].__setitem__("sta_clockerr", True))
def test_bad_state(): run_case(lambda r: r[0].__setitem__("time_state_name", "TIME_ERROR"))
def test_missing_field(): run_case(lambda r: r[0].pop("maxerror_ms"))
def test_too_large(): run_case(lambda r: r[0].__setitem__("maxerror_ms", 150.0))
def test_not_read_only(): run_case(lambda r: r[0].__setitem__("read_only_modes", 1))
def test_too_few():
    out=evaluate_kernel_clock_samples([base() for _ in range(4)])
    assert out["evidence_clock_eligible"] is False

if __name__ == "__main__":
    tests=[test_unsync,test_clockerr,test_bad_state,test_missing_field,test_too_large,test_not_read_only,test_too_few]
    for t in tests: t()
    print(f"A19B_KERNEL_CLOCK_EVIDENCE_ADVERSARIAL_TESTS_PASS {len(tests)}")
