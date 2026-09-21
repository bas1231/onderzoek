#!/usr/bin/env python3
"""A19C: fail-closed external clock evidence without installing a daemon.

This is an evidence probe, not a clock synchronizer. It never changes the
system clock. NTP/SNTP offset and delay use the standard four-timestamp
formula. Eligibility requires consensus from at least three distinct server
IPs and a conservative <=100 ms bound on local UTC error.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import ipaddress
import math
import socket
import statistics
import struct
import time
from typing import Callable

NTP_EPOCH = 2_208_988_800
NTP_PORT = 123
MAX_CLOCK_ERROR_MS = 100.0
MAX_SERVER_ROOT_MS = 1000.0
MAX_CLIENT_DELAY_MS = 500.0
DEFAULT_SERVERS = (
    "time.cloudflare.com",
    "time.google.com",
    "time.windows.com",
    "pool.ntp.org",
)


@dataclass(frozen=True)
class SntpSample:
    host: str
    server_ip: str
    version: int
    leap: int
    stratum: int
    offset_ms: float
    delay_ms: float
    root_delay_ms: float
    root_dispersion_ms: float
    wall_monotonic_divergence_ms: float
    sample_uncertainty_ms: float


def unix_ns_to_ntp64(unix_ns: int) -> int:
    sec, ns = divmod(int(unix_ns), 1_000_000_000)
    ntp_sec = sec + NTP_EPOCH
    frac = (ns << 32) // 1_000_000_000
    return ((ntp_sec & 0xFFFFFFFF) << 32) | (frac & 0xFFFFFFFF)


def ntp64_to_unix_ns(value: int) -> int:
    sec = (int(value) >> 32) & 0xFFFFFFFF
    frac = int(value) & 0xFFFFFFFF
    unix_sec = sec - NTP_EPOCH
    ns = (frac * 1_000_000_000) >> 32
    return unix_sec * 1_000_000_000 + ns


def _fixed_16_16_signed_ms(raw: bytes) -> float:
    value = struct.unpack("!i", raw)[0]
    return value * 1000.0 / 65536.0


def _fixed_16_16_unsigned_ms(raw: bytes) -> float:
    value = struct.unpack("!I", raw)[0]
    return value * 1000.0 / 65536.0


def parse_reply(
    data: bytes,
    *,
    host: str,
    server_ip: str,
    request_tx: int,
    t1_wall_ns: int,
    t4_wall_ns: int,
    t1_mono_ns: int,
    t4_mono_ns: int,
) -> SntpSample:
    if len(data) < 48:
        raise ValueError("SNTP reply shorter than 48 bytes")

    first = data[0]
    leap = (first >> 6) & 0x3
    version = (first >> 3) & 0x7
    mode = first & 0x7
    stratum = int(data[1])

    if version not in {3, 4}:
        raise ValueError("unsupported NTP version")
    if mode != 4:
        raise ValueError("reply is not unicast server mode")
    if leap == 3:
        raise ValueError("server reports unsynchronized leap alarm")
    if not 1 <= stratum <= 15:
        raise ValueError("invalid or unsynchronized stratum")

    root_delay_ms = _fixed_16_16_signed_ms(data[4:8])
    root_dispersion_ms = _fixed_16_16_unsigned_ms(data[8:12])
    if root_delay_ms < 0 or root_delay_ms >= MAX_SERVER_ROOT_MS:
        raise ValueError("implausible server root delay")
    if root_dispersion_ms < 0 or root_dispersion_ms >= MAX_SERVER_ROOT_MS:
        raise ValueError("implausible server root dispersion")

    originate = struct.unpack("!Q", data[24:32])[0]
    receive = struct.unpack("!Q", data[32:40])[0]
    transmit = struct.unpack("!Q", data[40:48])[0]
    if originate != request_tx:
        raise ValueError("originate timestamp does not match request transmit")
    if receive == 0 or transmit == 0:
        raise ValueError("server returned zero receive/transmit timestamp")

    t2_ns = ntp64_to_unix_ns(receive)
    t3_ns = ntp64_to_unix_ns(transmit)
    theta_ns = ((t2_ns - t1_wall_ns) + (t3_ns - t4_wall_ns)) / 2.0
    delay_ns = (t4_wall_ns - t1_wall_ns) - (t3_ns - t2_ns)
    delay_ms = delay_ns / 1_000_000.0
    if delay_ms < 0 or delay_ms > MAX_CLIENT_DELAY_MS:
        raise ValueError("implausible client/server round-trip delay")

    wall_elapsed_ns = t4_wall_ns - t1_wall_ns
    mono_elapsed_ns = t4_mono_ns - t1_mono_ns
    if mono_elapsed_ns < 0:
        raise ValueError("monotonic clock moved backwards")
    wall_mono_div_ms = abs(wall_elapsed_ns - mono_elapsed_ns) / 1_000_000.0

    # Conservative evidence bound, not an NTP daemon's formal root distance:
    # local path asymmetry + server upstream path + server dispersion + any
    # wall/monotonic discontinuity during the exchange + 1 ms scheduling floor.
    uncertainty_ms = (
        delay_ms / 2.0
        + root_delay_ms / 2.0
        + root_dispersion_ms
        + wall_mono_div_ms
        + 1.0
    )

    try:
        canonical_ip = str(ipaddress.ip_address(server_ip))
    except ValueError:
        canonical_ip = server_ip

    return SntpSample(
        host=host,
        server_ip=canonical_ip,
        version=version,
        leap=leap,
        stratum=stratum,
        offset_ms=round(theta_ns / 1_000_000.0, 6),
        delay_ms=round(delay_ms, 6),
        root_delay_ms=round(root_delay_ms, 6),
        root_dispersion_ms=round(root_dispersion_ms, 6),
        wall_monotonic_divergence_ms=round(wall_mono_div_ms, 6),
        sample_uncertainty_ms=round(uncertainty_ms, 6),
    )


def query_server(host: str, *, timeout: float = 1.5) -> SntpSample:
    errors: list[str] = []
    infos = socket.getaddrinfo(host, NTP_PORT, type=socket.SOCK_DGRAM)
    seen: set[tuple] = set()
    for family, socktype, proto, _, sockaddr in infos:
        key = (family, sockaddr)
        if key in seen:
            continue
        seen.add(key)
        sock = socket.socket(family, socktype, proto)
        try:
            sock.settimeout(timeout)
            t1_wall_ns = time.time_ns()
            t1_mono_ns = time.monotonic_ns()
            request_tx = unix_ns_to_ntp64(t1_wall_ns)
            packet = bytearray(48)
            packet[0] = (4 << 3) | 3  # VN=4, client mode=3
            packet[40:48] = struct.pack("!Q", request_tx)
            sock.sendto(packet, sockaddr)
            data, peer = sock.recvfrom(512)
            t4_wall_ns = time.time_ns()
            t4_mono_ns = time.monotonic_ns()
            server_ip = str(peer[0])
            return parse_reply(
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
    raise RuntimeError(f"no valid SNTP reply from {host}: {'; '.join(errors[-4:])}")


def aggregate_samples(samples: list[SntpSample], errors: dict[str, str] | None = None) -> dict:
    # One vote per distinct server IP prevents DNS aliases/retries from
    # manufacturing consensus.
    by_ip: dict[str, SntpSample] = {}
    for sample in samples:
        previous = by_ip.get(sample.server_ip)
        if previous is None or sample.sample_uncertainty_ms < previous.sample_uncertainty_ms:
            by_ip[sample.server_ip] = sample
    unique = list(by_ip.values())

    out = {
        "clock_source": "sntp_consensus",
        "clock_offset_ms": None,
        "clock_uncertainty_ms": None,
        "clock_uncertainty_semantics": (
            "max over distinct servers of sample_uncertainty + deviation from median offset; "
            "sample_uncertainty=client_delay/2+root_delay/2+root_dispersion+wall_monotonic_divergence+1ms"
        ),
        "evidence_clock_eligible": False,
        "sample_count": len(unique),
        "required_distinct_servers": 3,
        "samples": [asdict(s) for s in sorted(unique, key=lambda s: (s.host, s.server_ip))],
        "errors": dict(sorted((errors or {}).items())),
        "max_clock_error_gate_ms": MAX_CLOCK_ERROR_MS,
    }
    if len(unique) < 3:
        out["detail"] = "fewer than three distinct valid SNTP server IPs"
        return out

    offsets = [s.offset_ms for s in unique]
    median_offset = float(statistics.median(offsets))
    uncertainty = max(
        s.sample_uncertainty_ms + abs(s.offset_ms - median_offset)
        for s in unique
    )
    total_error_bound = abs(median_offset) + uncertainty

    out.update({
        "clock_offset_ms": round(median_offset, 6),
        "clock_uncertainty_ms": round(uncertainty, 6),
        "clock_total_error_bound_ms": round(total_error_bound, 6),
        "offset_span_ms": round(max(offsets) - min(offsets), 6),
        "evidence_clock_eligible": bool(
            math.isfinite(total_error_bound)
            and total_error_bound <= MAX_CLOCK_ERROR_MS
        ),
        "detail": "SNTP consensus within gate" if total_error_bound <= MAX_CLOCK_ERROR_MS else "SNTP consensus exceeds error gate",
    })
    return out


_CACHE: tuple[int, dict] | None = None
CACHE_TTL_NS = 30_000_000_000


def collect_clock_evidence(
    servers: tuple[str, ...] = DEFAULT_SERVERS,
    *,
    query: Callable[[str], SntpSample] | None = None,
) -> dict:
    fn = query or query_server
    samples: list[SntpSample] = []
    errors: dict[str, str] = {}
    started_ns = time.time_ns()
    for host in servers:
        try:
            samples.append(fn(host))
        except Exception as exc:
            errors[host] = f"{type(exc).__name__}: {exc}"
    result = aggregate_samples(samples, errors)
    result["evidence_collected_at_ns"] = started_ns
    result["evidence_collected_at_unix_s"] = started_ns / 1_000_000_000.0
    return result


def clock_health() -> dict:
    global _CACHE
    now_mono = time.monotonic_ns()
    if _CACHE is not None:
        cached_mono, cached = _CACHE
        age_ns = now_mono - cached_mono
        if 0 <= age_ns <= CACHE_TTL_NS:
            out = dict(cached)
            out["evidence_cache_age_ms"] = round(age_ns / 1_000_000.0, 3)
            return out
    result = collect_clock_evidence()
    _CACHE = (time.monotonic_ns(), dict(result))
    result["evidence_cache_age_ms"] = 0.0
    return result


if __name__ == "__main__":
    import json
    print(json.dumps(collect_clock_evidence(), indent=2, sort_keys=True))
