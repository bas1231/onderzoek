#!/usr/bin/env python3
"""A19B-v2 direct UTC evidence from NIST Internet Time Service.

Read-only only: this module never changes the system clock.  It sends one NTP
request to each of three named NIST stratum-1 servers and derives a conservative
UTC correction interval for the local CLOCK_REALTIME value.

Per-source uncertainty radius:
    root_dispersion + abs(root_delay)/2 + max(path_delay, 0)/2 + 1 ms guard

The project evidence gate is intentionally stricter than merely obtaining NTP
responses: every configured source must be valid, stratum 1, individually
bounded within CLOCK_MAX_UNCERTAINTY_MS, and all source correction intervals
must have a non-empty intersection whose maximum absolute endpoint is also
within the limit.

NIST anonymous ITS NTP is not cryptographically authenticated.  That provenance
limitation is carried explicitly in the evidence and this is research timing
evidence, not regulatory traceability evidence.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
import socket
import struct
import time
from typing import Iterable

NTP_EPOCH_DELTA = 2_208_988_800
NTP_PACKET_BYTES = 48
CLOCK_MAX_UNCERTAINTY_MS = 100.0
LOCAL_SERIALIZATION_GUARD_MS = 1.0
SOCKET_TIMEOUT_SECONDS = 2.5

# Current active public NIST ITS endpoints, intentionally spread across three
# NIST locations.  Each is queried at most once in one probe run.
NIST_SERVERS = (
    "time-a-g.nist.gov",     # Gaithersburg, Maryland
    "time-a-wwv.nist.gov",   # WWV, Fort Collins, Colorado
    "time-a-b.nist.gov",     # Boulder, Colorado
)


class NtpEvidenceError(ValueError):
    pass


def _unix_to_ntp64(ts: float) -> bytes:
    if not math.isfinite(ts):
        raise NtpEvidenceError("non-finite local timestamp")
    ntp = ts + NTP_EPOCH_DELTA
    sec = int(math.floor(ntp))
    frac = int((ntp - sec) * (1 << 32))
    return struct.pack("!II", sec & 0xFFFFFFFF, frac & 0xFFFFFFFF)


def _ntp64_to_unix(raw: bytes) -> float:
    if len(raw) != 8:
        raise NtpEvidenceError("invalid NTP timestamp length")
    sec, frac = struct.unpack("!II", raw)
    if sec == 0 and frac == 0:
        raise NtpEvidenceError("zero NTP timestamp")
    return float(sec - NTP_EPOCH_DELTA) + float(frac) / float(1 << 32)


def build_request(t1_unix: float) -> tuple[bytes, bytes]:
    packet = bytearray(NTP_PACKET_BYTES)
    packet[0] = 0x23  # LI=0, VN=4, mode=3 (client)
    tx = _unix_to_ntp64(t1_unix)
    packet[40:48] = tx
    return bytes(packet), tx


def parse_response(
    packet: bytes,
    *,
    request_tx: bytes,
    t1_unix: float,
    t4_unix: float,
    server_name: str,
    server_ip: str,
) -> dict:
    if len(packet) < NTP_PACKET_BYTES:
        raise NtpEvidenceError("truncated NTP response")
    if len(request_tx) != 8:
        raise NtpEvidenceError("invalid request transmit timestamp")
    if not (math.isfinite(t1_unix) and math.isfinite(t4_unix)):
        raise NtpEvidenceError("non-finite local receive timestamps")
    if t4_unix < t1_unix:
        raise NtpEvidenceError("local realtime moved backwards during NTP exchange")

    li = (packet[0] >> 6) & 0x3
    version = (packet[0] >> 3) & 0x7
    mode = packet[0] & 0x7
    stratum = int(packet[1])

    if li == 3:
        raise NtpEvidenceError("NTP server reports unsynchronized leap state")
    if version not in {3, 4}:
        raise NtpEvidenceError(f"unsupported NTP version: {version}")
    if mode != 4:
        raise NtpEvidenceError(f"response is not NTP server mode: {mode}")
    if stratum != 1:
        raise NtpEvidenceError(f"NIST evidence source is not stratum 1: {stratum}")

    originate = packet[24:32]
    if originate != request_tx:
        raise NtpEvidenceError("NTP originate timestamp does not match request")

    t2 = _ntp64_to_unix(packet[32:40])
    t3 = _ntp64_to_unix(packet[40:48])
    if t3 < t2:
        raise NtpEvidenceError("NTP transmit timestamp precedes receive timestamp")

    root_delay_s = float(struct.unpack("!i", packet[4:8])[0]) / 65536.0
    root_dispersion_s = float(struct.unpack("!I", packet[8:12])[0]) / 65536.0
    if root_dispersion_s < 0 or not math.isfinite(root_dispersion_s):
        raise NtpEvidenceError("invalid root dispersion")

    path_delay_s = (t4_unix - t1_unix) - (t3 - t2)
    # Tiny negative values can arise from timestamp quantization.  Anything
    # materially negative makes the evidence unusable.
    if path_delay_s < -0.001:
        raise NtpEvidenceError("negative NTP path delay")
    path_delay_s = max(0.0, path_delay_s)

    offset_s = ((t2 - t1_unix) + (t3 - t4_unix)) / 2.0
    root_distance_s = root_dispersion_s + abs(root_delay_s) / 2.0
    uncertainty_radius_s = (
        root_distance_s
        + path_delay_s / 2.0
        + LOCAL_SERIALIZATION_GUARD_MS / 1000.0
    )
    interval_low_s = offset_s - uncertainty_radius_s
    interval_high_s = offset_s + uncertainty_radius_s
    individual_bound_ms = max(abs(interval_low_s), abs(interval_high_s)) * 1000.0

    refid = packet[12:16]
    return {
        "status": "PASS",
        "server_name": server_name,
        "server_ip": server_ip,
        "authentication": "UNAUTHENTICATED_NIST_ITS_NTP",
        "leap_indicator": li,
        "version": version,
        "mode": mode,
        "stratum": stratum,
        "reference_id_hex": refid.hex(),
        "root_delay_ms": round(root_delay_s * 1000.0, 6),
        "root_dispersion_ms": round(root_dispersion_s * 1000.0, 6),
        "root_distance_ms": round(root_distance_s * 1000.0, 6),
        "path_delay_ms": round(path_delay_s * 1000.0, 6),
        "offset_ms": round(offset_s * 1000.0, 6),
        "uncertainty_radius_ms": round(uncertainty_radius_s * 1000.0, 6),
        "correction_interval_low_ms": round(interval_low_s * 1000.0, 6),
        "correction_interval_high_ms": round(interval_high_s * 1000.0, 6),
        "individual_absolute_error_bound_ms": round(individual_bound_ms, 6),
        "t1_unix": t1_unix,
        "t2_unix": t2,
        "t3_unix": t3,
        "t4_unix": t4_unix,
    }


def query_server(server_name: str, *, timeout: float = SOCKET_TIMEOUT_SECONDS) -> dict:
    try:
        infos = socket.getaddrinfo(
            server_name,
            123,
            family=socket.AF_INET,
            type=socket.SOCK_DGRAM,
        )
        if not infos:
            raise NtpEvidenceError("no IPv4 NTP address resolved")
        server_ip = str(infos[0][4][0])

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            t1 = time.time()
            request, request_tx = build_request(t1)
            sock.sendto(request, (server_ip, 123))
            packet, source = sock.recvfrom(512)
            t4 = time.time()

        source_ip = str(source[0])
        if source_ip != server_ip:
            raise NtpEvidenceError(
                f"response source mismatch: expected={server_ip} actual={source_ip}"
            )
        return parse_response(
            packet,
            request_tx=request_tx,
            t1_unix=t1,
            t4_unix=t4,
            server_name=server_name,
            server_ip=server_ip,
        )
    except Exception as exc:
        return {
            "status": "BLOCKED",
            "server_name": server_name,
            "authentication": "UNAUTHENTICATED_NIST_ITS_NTP",
            "reason": f"{type(exc).__name__}: {exc}",
        }


def evaluate_samples(
    samples: Iterable[dict],
    *,
    limit_ms: float = CLOCK_MAX_UNCERTAINTY_MS,
    expected_count: int = len(NIST_SERVERS),
) -> dict:
    rows = list(samples)
    reasons: list[str] = []
    valid = [row for row in rows if row.get("status") == "PASS"]

    if len(rows) != expected_count:
        reasons.append("SAMPLE_COUNT_MISMATCH")
    if len(valid) != expected_count:
        reasons.append("NOT_ALL_NIST_SOURCES_VALID")

    names = {str(row.get("server_name")) for row in valid}
    ips = {str(row.get("server_ip")) for row in valid}
    if len(names) != expected_count:
        reasons.append("NIST_SERVER_NAME_DIVERSITY_FAILED")
    if len(ips) != expected_count:
        reasons.append("NIST_SERVER_IP_DIVERSITY_FAILED")

    for idx, row in enumerate(valid):
        if int(row.get("stratum", 0)) != 1:
            reasons.append(f"SAMPLE_{idx}_NOT_STRATUM_1")
        bound = float(row.get("individual_absolute_error_bound_ms", math.inf))
        if not math.isfinite(bound) or bound > limit_ms:
            reasons.append(f"SAMPLE_{idx}_BOUND_ABOVE_LIMIT")

    intersection_low_ms = None
    intersection_high_ms = None
    intersection_bound_ms = None
    if len(valid) == expected_count:
        lows = [float(row["correction_interval_low_ms"]) for row in valid]
        highs = [float(row["correction_interval_high_ms"]) for row in valid]
        intersection_low_ms = max(lows)
        intersection_high_ms = min(highs)
        if intersection_low_ms > intersection_high_ms:
            reasons.append("NO_COMMON_UTC_CORRECTION_INTERVAL")
        else:
            intersection_bound_ms = max(
                abs(intersection_low_ms), abs(intersection_high_ms)
            )
            if intersection_bound_ms > limit_ms:
                reasons.append("CONSENSUS_BOUND_ABOVE_LIMIT")

    eligible = not reasons
    return {
        "schema": "A19B_NIST_NTP_CLOCK_EVIDENCE_V1",
        "decision": "CLOCK_EVIDENCE_ELIGIBLE" if eligible else "CLOCK_EVIDENCE_BLOCKED",
        "evidence_clock_eligible": eligible,
        "max_uncertainty_limit_ms": limit_ms,
        "source_count": len(rows),
        "valid_source_count": len(valid),
        "source_names": sorted(names),
        "source_ips": sorted(ips),
        "consensus_correction_interval_low_ms": intersection_low_ms,
        "consensus_correction_interval_high_ms": intersection_high_ms,
        "consensus_absolute_error_bound_ms": intersection_bound_ms,
        "reasons": sorted(set(reasons)),
        "uncertainty_semantics": (
            "per-source correction interval = NTP offset +/- "
            "(root_dispersion + abs(root_delay)/2 + path_delay/2 + 1ms guard); "
            "all configured NIST stratum-1 source intervals must intersect"
        ),
        "provenance_limitation": (
            "NIST ITS anonymous NTP is not cryptographically authenticated; "
            "used as research clock evidence, not regulatory traceability proof"
        ),
    }


def probe() -> dict:
    samples = [query_server(server) for server in NIST_SERVERS]
    decision = evaluate_samples(samples)
    return {
        "task": "WX-A19B-V2-NIST-NTP-CLOCK-PROBE",
        "status": "PROBE_COMPLETE",
        "changes_system_clock": False,
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
        "economic_conclusion": "NO_PROVEN_EDGE",
        "servers": list(NIST_SERVERS),
        "samples": samples,
        "clock_evidence": decision,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()
    if not args.probe:
        parser.error("--probe is required; this tool is read-only and probe-only")
    result = probe()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
