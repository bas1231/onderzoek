#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control" / "weather"))

import clock_evidence_sntp_a19c as base
import clock_evidence_transport_a19d as a19d


def sample(host: str, ip: str, offset: float, uncertainty: float = 8.0) -> base.SntpSample:
    return base.SntpSample(
        host=host,
        server_ip=ip,
        version=4,
        leap=0,
        stratum=2,
        offset_ms=offset,
        delay_ms=10.0,
        root_delay_ms=2.0,
        root_dispersion_ms=1.0,
        wall_monotonic_divergence_ms=0.1,
        sample_uncertainty_ms=uncertainty,
    )


def test_round_requires_distinct_provider_hosts_and_ips():
    mapping = {
        "a": sample("a", "192.0.2.1", 1.0),
        "b": sample("b", "192.0.2.2", 2.0),
        "c": sample("c", "192.0.2.3", 1.5),
    }
    out = a19d.collect_round(("a", "b", "c"), query=lambda host: mapping[host])
    assert out["evidence_clock_eligible"] is True
    assert out["provider_count"] == 3
    assert out["distinct_server_ip_count"] == 3


def test_same_ip_cannot_supply_three_provider_consensus():
    mapping = {
        "a": sample("a", "192.0.2.1", 1.0),
        "b": sample("b", "192.0.2.1", 1.5),
        "c": sample("c", "192.0.2.2", 1.2),
    }
    out = a19d.collect_round(("a", "b", "c"), query=lambda host: mapping[host])
    assert out["evidence_clock_eligible"] is False
    assert out["provider_gate_pass"] is True
    assert out["server_ip_gate_pass"] is False


def eligible_round(offset: float, bound: float = 20.0) -> dict:
    return {
        "evidence_clock_eligible": True,
        "clock_offset_ms": offset,
        "clock_total_error_bound_ms": bound,
    }


def test_five_consecutive_rounds_can_open_transport_gate():
    rounds = [eligible_round(v) for v in (1.0, 1.5, 2.0, 1.2, 1.8)]
    out = a19d.aggregate_rounds(rounds, required_rounds=5)
    assert out["evidence_clock_eligible"] is True
    assert out["clock_total_error_bound_ms"] <= 100.0
    assert out["cross_round_offset_span_ms"] < 2.0


def test_missing_round_fails_closed():
    rounds = [eligible_round(1.0) for _ in range(4)]
    out = a19d.aggregate_rounds(rounds, required_rounds=5)
    assert out["evidence_clock_eligible"] is False
    assert "required number" in out["detail"]


def test_cross_round_disagreement_fails_closed():
    rounds = [
        eligible_round(0.0, 10.0),
        eligible_round(1.0, 10.0),
        eligible_round(-1.0, 10.0),
        eligible_round(2.0, 10.0),
        eligible_round(130.0, 10.0),
    ]
    out = a19d.aggregate_rounds(rounds, required_rounds=5)
    assert out["evidence_clock_eligible"] is False
    assert out["cross_round_offset_span_ms"] > 100.0


def test_probe_with_injected_query_is_read_only_and_structured():
    mapping = {
        "a": sample("a", "192.0.2.1", 1.0),
        "b": sample("b", "192.0.2.2", 1.5),
        "c": sample("c", "192.0.2.3", 2.0),
    }
    out = a19d.collect_transport_evidence(
        ("a", "b", "c"),
        rounds=5,
        pause_seconds=0.0,
        query=lambda host: mapping[host],
        sleep_fn=lambda _: None,
    )
    assert out["schema"] == "WEATHER_CLOCK_TRANSPORT_A19D_V1"
    assert out["read_only"] is True
    assert out["clock_adjustment_performed"] is False
    assert out["evidence_clock_eligible"] is True
    assert out["economic_conclusion"] == "NO_PROVEN_EDGE"


if __name__ == "__main__":
    tests = [
        test_round_requires_distinct_provider_hosts_and_ips,
        test_same_ip_cannot_supply_three_provider_consensus,
        test_five_consecutive_rounds_can_open_transport_gate,
        test_missing_round_fails_closed,
        test_cross_round_disagreement_fails_closed,
        test_probe_with_injected_query_is_read_only_and_structured,
    ]
    for test in tests:
        test()
    print(f"CLOCK_EVIDENCE_TRANSPORT_A19D_UNIT_TESTS_PASS {len(tests)}")
