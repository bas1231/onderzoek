#!/usr/bin/env python3
"""A19D: read-only transport clock evidence for Weather latency research.

This module does not synchronize or change the local clock. It performs direct
NTP client exchanges over UDP/123 from the same runtime that timestamps Weather
observations. Packet parsing and per-sample uncertainty reuse the already-tested
A19C SNTP implementation.

Evidence semantics are deliberately conservative:
- one round queries independent provider hostnames;
- a round needs >=3 distinct valid provider hostnames AND >=3 distinct server IPs;
- five consecutive rounds are required by the default prospective gate;
- the final error bound includes each round's own conservative bound plus
  cross-round offset disagreement;
- ordinary NTP is unauthenticated, so this is transport-consensus evidence, not
  cryptographic UTC attestation.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import socket
import statistics
import struct
import sys
import time
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control" / "weather"))

import clock_evidence_sntp_a19c as base  # noqa: E402

DEFAULT_PROVIDERS = (
    "time.cloudflare.com",
    "time.google.com",
    "time.windows.com",
    "time.nist.gov",
)

DEFAULT_ROUNDS = 5
MIN_DISTINCT_PROVIDERS = 3
MIN_DISTINCT_SERVER_IPS = 3
MAX_TOTAL_ERROR_MS = 100.0
MAX_CROSS_ROUND_OFFSET_SPAN_MS = 100.0


def query_server_connected(host: str, *, timeout: float = 1.5) -> base.SntpSample:
    """Query one NTP hostname using a connected UDP socket.

    UDP connect() does not create a session, but it constrains receive delivery
    to the selected peer address/port. The NTP originate-timestamp equality
    check in base.parse_reply() remains mandatory as a second anti-mismatch
    check.
    """
    errors: list[str] = []
    infos = socket.getaddrinfo(host, base.NTP_PORT, type=socket.SOCK_DGRAM)
    seen: set[tuple] = set()

    for family, socktype, proto, _, sockaddr in infos:
        key = (family, sockaddr)
        if key in seen:
            continue
        seen.add(key)

        sock = socket.socket(family, socktype, proto)
        try:
            sock.settimeout(timeout)
            sock.connect(sockaddr)

            t1_wall_ns = time.time_ns()
            t1_mono_ns = time.monotonic_ns()
            request_tx = base.unix_ns_to_ntp64(t1_wall_ns)

            packet = bytearray(48)
            packet[0] = (4 << 3) | 3  # VN=4, client mode=3
            packet[40:48] = struct.pack("!Q", request_tx)

            sock.send(packet)
            data = sock.recv(512)
            t4_wall_ns = time.time_ns()
            t4_mono_ns = time.monotonic_ns()

            server_ip = str(sock.getpeername()[0])
            return base.parse_reply(
                data,
                host=host,
                server_ip=server_ip,
                request_tx=request_tx,
                t1_wall_ns=t1_wall_ns,
                t4_wall_ns=t4_wall_ns,
                t1_mono_ns=t1_mono_ns,
                t4_mono_ns=t4_mono_ns,
            )
        except Exception as exc:
            errors.append(f"{type(exc).__name__}:{exc}")
        finally:
            sock.close()

    raise RuntimeError(
        f"no valid connected NTP reply from {host}: {'; '.join(errors[-6:])}"
    )


def collect_round(
    providers: tuple[str, ...] = DEFAULT_PROVIDERS,
    *,
    query: Callable[[str], base.SntpSample] | None = None,
) -> dict:
    fn = query or query_server_connected
    samples: list[base.SntpSample] = []
    errors: dict[str, str] = {}

    for host in providers:
        try:
            samples.append(fn(host))
        except Exception as exc:
            errors[host] = f"{type(exc).__name__}: {exc}"

    consensus = base.aggregate_samples(samples, errors)
    distinct_hosts = sorted({sample.host for sample in samples})
    distinct_ips = sorted({sample.server_ip for sample in samples})

    provider_gate = len(distinct_hosts) >= MIN_DISTINCT_PROVIDERS
    ip_gate = len(distinct_ips) >= MIN_DISTINCT_SERVER_IPS
    round_eligible = bool(
        consensus.get("evidence_clock_eligible") is True
        and provider_gate
        and ip_gate
    )

    return {
        "status": "PASS" if round_eligible else "BLOCKED",
        "evidence_clock_eligible": round_eligible,
        "provider_count": len(distinct_hosts),
        "distinct_providers": distinct_hosts,
        "distinct_server_ip_count": len(distinct_ips),
        "distinct_server_ips": distinct_ips,
        "provider_gate_pass": provider_gate,
        "server_ip_gate_pass": ip_gate,
        "clock_offset_ms": consensus.get("clock_offset_ms"),
        "clock_uncertainty_ms": consensus.get("clock_uncertainty_ms"),
        "clock_total_error_bound_ms": consensus.get("clock_total_error_bound_ms"),
        "offset_span_ms": consensus.get("offset_span_ms"),
        "samples": consensus.get("samples", []),
        "errors": consensus.get("errors", {}),
        "consensus_detail": consensus.get("detail"),
    }


def aggregate_rounds(rounds: list[dict], *, required_rounds: int = DEFAULT_ROUNDS) -> dict:
    structurally_valid = [
        row for row in rounds
        if isinstance(row, dict)
        and isinstance(row.get("evidence_clock_eligible"), bool)
    ]
    eligible = [row for row in structurally_valid if row["evidence_clock_eligible"]]

    out = {
        "clock_source": "multi-provider-ntp-transport-consensus",
        "authentication": "ordinary NTP; unauthenticated",
        "network_adversary_resistant": False,
        "read_only": True,
        "clock_adjustment_performed": False,
        "round_count": len(rounds),
        "structurally_valid_round_count": len(structurally_valid),
        "eligible_round_count": len(eligible),
        "required_consecutive_rounds": required_rounds,
        "required_distinct_providers_per_round": MIN_DISTINCT_PROVIDERS,
        "required_distinct_server_ips_per_round": MIN_DISTINCT_SERVER_IPS,
        "clock_offset_ms": None,
        "clock_uncertainty_ms": None,
        "clock_total_error_bound_ms": None,
        "cross_round_offset_span_ms": None,
        "evidence_clock_eligible": False,
        "rounds": rounds,
        "max_total_error_gate_ms": MAX_TOTAL_ERROR_MS,
    }

    if len(rounds) != required_rounds or len(structurally_valid) != required_rounds:
        out["detail"] = "required number of structurally valid rounds not obtained"
        return out

    if len(eligible) != required_rounds:
        out["detail"] = "not all consecutive transport rounds were eligible"
        return out

    offsets = [float(row["clock_offset_ms"]) for row in eligible]
    bounds = [float(row["clock_total_error_bound_ms"]) for row in eligible]
    if not all(math.isfinite(value) for value in offsets + bounds):
        out["detail"] = "non-finite transport evidence"
        return out

    median_offset = float(statistics.median(offsets))
    cross_span = max(offsets) - min(offsets)

    # Each round's total bound already includes abs(local offset). For a
    # cross-round bound we conservatively add disagreement from the median.
    final_total_bound = max(
        bound + abs(offset - median_offset)
        for bound, offset in zip(bounds, offsets)
    )
    final_uncertainty = max(0.0, final_total_bound - abs(median_offset))

    eligible_final = bool(
        cross_span <= MAX_CROSS_ROUND_OFFSET_SPAN_MS
        and final_total_bound <= MAX_TOTAL_ERROR_MS
    )

    out.update({
        "clock_offset_ms": round(median_offset, 6),
        "clock_uncertainty_ms": round(final_uncertainty, 6),
        "clock_total_error_bound_ms": round(final_total_bound, 6),
        "cross_round_offset_span_ms": round(cross_span, 6),
        "evidence_clock_eligible": eligible_final,
        "detail": (
            "five-round transport consensus within gate"
            if eligible_final
            else "five-round transport consensus exceeds gate"
        ),
    })
    return out


def collect_transport_evidence(
    providers: tuple[str, ...] = DEFAULT_PROVIDERS,
    *,
    rounds: int = DEFAULT_ROUNDS,
    pause_seconds: float = 0.05,
    query: Callable[[str], base.SntpSample] | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> dict:
    observations: list[dict] = []
    started_wall_ns = time.time_ns()
    started_mono_ns = time.monotonic_ns()

    for index in range(rounds):
        observation = collect_round(providers, query=query)
        observation["round_index"] = index
        observation["sampled_at_ns"] = time.time_ns()
        observations.append(observation)
        if index + 1 < rounds and pause_seconds > 0:
            sleep_fn(pause_seconds)

    finished_wall_ns = time.time_ns()
    finished_mono_ns = time.monotonic_ns()
    result = aggregate_rounds(observations, required_rounds=rounds)
    result.update({
        "schema": "WEATHER_CLOCK_TRANSPORT_A19D_V1",
        "task": "WX-A19D-TRANSPORT-CLOCK-EVIDENCE",
        "started_at_ns": started_wall_ns,
        "finished_at_ns": finished_wall_ns,
        "probe_duration_ms": round((finished_mono_ns - started_mono_ns) / 1_000_000.0, 3),
        "wall_monotonic_probe_divergence_ms": round(
            abs(
                (finished_wall_ns - started_wall_ns)
                - (finished_mono_ns - started_mono_ns)
            ) / 1_000_000.0,
            6,
        ),
        "provider_hosts": list(providers),
        "economic_conclusion": "NO_PROVEN_EDGE",
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
        "openai_api": False,
    })
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS)
    parser.add_argument("--pause-seconds", type=float, default=0.05)
    parser.add_argument("--providers", nargs="*", default=list(DEFAULT_PROVIDERS))
    args = parser.parse_args()

    if args.rounds < 1 or args.rounds > 20:
        raise SystemExit("rounds must be between 1 and 20")
    providers = tuple(str(value).strip() for value in args.providers if str(value).strip())
    if len(set(providers)) < MIN_DISTINCT_PROVIDERS:
        raise SystemExit("at least three distinct provider hostnames are required")

    result = collect_transport_evidence(
        providers,
        rounds=args.rounds,
        pause_seconds=max(0.0, args.pause_seconds),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    # Probe execution success is distinct from evidence eligibility. The
    # validator decides whether the research gate remains blocked.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
