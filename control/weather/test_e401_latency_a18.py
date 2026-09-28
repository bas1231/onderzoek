#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control" / "weather"))

import e401_latency_a18 as m


def test_percentiles_small_samples():
    xs = [100, 200, 300, 400, 500]
    assert m.percentile(xs, 0.0) == 100
    assert m.percentile(xs, 0.5) == 300
    assert m.percentile(xs, 0.9) == 500
    assert m.percentile(xs, 1.0) == 500


def test_bins_are_non_overlapping():
    result = m.latency_bins([1000, 1001, 3000, 3001, 10000, 10001, 30000, 30001])
    assert result == {
        "le_1s": 1,
        "gt_1s_le_3s": 2,
        "gt_3s_le_10s": 2,
        "gt_10s_le_30s": 2,
        "gt_30s": 1,
    }


def test_empty_stats_fail_neutral():
    result = m.stats([])
    assert result["n"] == 0
    assert result["median_ms"] is None
    assert sum(result["bins"].values()) == 0


if __name__ == "__main__":
    tests = [test_percentiles_small_samples, test_bins_are_non_overlapping, test_empty_stats_fail_neutral]
    for test in tests:
        test()
    print(f"E401_A18_LATENCY_TESTS_PASS {len(tests)}")
