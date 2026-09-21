#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import time

WEATHER_ROOT = Path.home() / "prediction_research_weather"
PROJECT_PYTHON = Path.home() / "prediction_research/.venv/bin/python"
A19C_VALIDATOR = WEATHER_ROOT / "control/jobs/validate_clock_evidence_a19c.py"


def run(args: list[str], *, cwd: Path | None = None, timeout: int = 20) -> dict:
    try:
        cp = subprocess.run(
            args,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return {
            "command": args,
            "returncode": cp.returncode,
            "stdout": cp.stdout[-20000:],
            "stderr": cp.stderr[-10000:],
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": args,
            "returncode": 124,
            "stdout": (exc.stdout or "")[-20000:] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "")[-10000:] if isinstance(exc.stderr, str) else "",
            "timed_out": True,
        }
    except Exception as exc:
        return {
            "command": args,
            "returncode": 125,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
            "timed_out": False,
        }


def parse_json(text: str) -> dict:
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def find_windows_exe(name: str, fallback: str) -> str | None:
    hit = shutil.which(name)
    if hit:
        return hit
    path = Path(fallback)
    return str(path) if path.is_file() else None


def sample_windows_utc_ms(powershell: str, n: int = 5) -> dict:
    rows = []
    cmd = [
        powershell,
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        "[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()",
    ]
    for _ in range(n):
        t0_wall_ns = time.time_ns()
        t0_mono_ns = time.monotonic_ns()
        cp = run(cmd, timeout=5)
        t1_mono_ns = time.monotonic_ns()
        t1_wall_ns = time.time_ns()
        row = {
            "returncode": cp["returncode"],
            "stderr": cp["stderr"][-1000:],
            "roundtrip_ms": round((t1_mono_ns - t0_mono_ns) / 1_000_000.0, 3),
        }
        try:
            host_ms = int(cp["stdout"].strip().splitlines()[-1])
            linux_mid_ms = (t0_wall_ns + t1_wall_ns) / 2_000_000.0
            offset = host_ms - linux_mid_ms
            row.update({
                "windows_utc_ms": host_ms,
                "linux_midpoint_utc_ms": linux_mid_ms,
                "windows_minus_linux_ms": round(offset, 3),
                "transport_uncertainty_ms": round((t1_mono_ns - t0_mono_ns) / 2_000_000.0 + 1.0, 3),
            })
        except Exception:
            row["parse_error"] = True
        rows.append(row)
        time.sleep(0.05)

    offsets = [r["windows_minus_linux_ms"] for r in rows if "windows_minus_linux_ms" in r]
    uncertainties = [r["transport_uncertainty_ms"] for r in rows if "transport_uncertainty_ms" in r]
    return {
        "samples": rows,
        "valid_samples": len(offsets),
        "median_windows_minus_linux_ms": None if not offsets else round(statistics.median(offsets), 3),
        "max_transport_uncertainty_ms": None if not uncertainties else max(uncertainties),
        "offset_span_ms": None if len(offsets) < 2 else round(max(offsets) - min(offsets), 3),
    }


def classify(sntp_offset_ms: float | None, host_minus_linux_ms: float | None, host_unc_ms: float | None) -> dict:
    out = {
        "classification": "INCONCLUSIVE",
        "reason": "insufficient evidence",
        "safe_to_modify_clock": False,
    }
    if sntp_offset_ms is None or host_minus_linux_ms is None or host_unc_ms is None:
        return out

    # SNTP offset semantics: external-reference time minus Linux/WSL local time.
    # Therefore, if Windows is externally correct, Windows-Linux should agree
    # numerically with the SNTP offset within measurement uncertainty.
    tolerance_ms = max(100.0, host_unc_ms + 75.0)
    if abs(sntp_offset_ms) <= 100.0:
        out.update({
            "classification": "CLOCK_WITHIN_RESEARCH_GATE",
            "reason": "fresh SNTP offset is within 100 ms",
        })
    elif abs(host_minus_linux_ms - sntp_offset_ms) <= tolerance_ms:
        out.update({
            "classification": "WSL_GUEST_DRIFT_FROM_WINDOWS_HOST",
            "reason": "Windows-Linux offset agrees with SNTP-Linux offset",
        })
    elif abs(host_minus_linux_ms) <= tolerance_ms:
        out.update({
            "classification": "WINDOWS_HOST_AND_WSL_SHARE_EXTERNAL_OFFSET",
            "reason": "Windows and WSL agree with each other but both differ from SNTP",
        })
    else:
        out.update({
            "classification": "MULTI_CLOCK_MISMATCH",
            "reason": "Windows-Linux and SNTP-Linux offsets disagree materially",
        })
    return out


result = {
    "task": "WEATHER-A19C2-CLOCK-TRANSPORT-DIAGNOSTIC",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "openai_api": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
    "checks": {},
}

# CHECK 1/3 — technical/read-only prerequisites.
powershell = find_windows_exe(
    "powershell.exe",
    "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
)
check1 = bool(PROJECT_PYTHON.is_file() and A19C_VALIDATOR.is_file() and powershell)
result["checks"]["check_1_technical"] = {
    "pass": check1,
    "project_python": str(PROJECT_PYTHON),
    "a19c_validator": str(A19C_VALIDATOR),
    "powershell": powershell,
}

# CHECK 2/3 — fail-closed transport semantics. We require multiple valid host
# samples with bounded spread; no host-time conclusion from a single subprocess.
host = sample_windows_utc_ms(powershell, 5) if check1 else {"samples": [], "valid_samples": 0}
host_spread = host.get("offset_span_ms")
host_unc = host.get("max_transport_uncertainty_ms")
check2 = bool(
    check1
    and host.get("valid_samples", 0) >= 3
    and host_spread is not None
    and host_spread <= 100.0
    and host_unc is not None
    and host_unc <= 1000.0
)
result["checks"]["check_2_fail_closed_transport"] = {
    "pass": check2,
    "host_clock_transport": host,
    "requirements": {
        "min_valid_samples": 3,
        "max_offset_span_ms": 100.0,
        "max_transport_uncertainty_ms": 1000.0,
    },
}

# CHECK 3/3 — fresh live SNTP evidence + Windows Time read-only status.
clock_validation = run(
    [str(PROJECT_PYTHON), str(A19C_VALIDATOR.relative_to(WEATHER_ROOT))],
    cwd=WEATHER_ROOT,
    timeout=60,
) if check2 else {"returncode": 125, "stdout": "", "stderr": "SKIPPED", "timed_out": False}
clock_obj = parse_json(clock_validation.get("stdout", ""))
clock = clock_obj.get("clock_readiness") or {}
sntp_offset = clock.get("clock_offset_ms")

w32tm_status = run([powershell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", "w32tm /query /status /verbose"], timeout=10) if check2 else {}
w32tm_source = run([powershell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", "w32tm /query /source"], timeout=10) if check2 else {}
w32tm_peers = run([powershell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", "w32tm /query /peers"], timeout=10) if check2 else {}

classification = classify(
    float(sntp_offset) if isinstance(sntp_offset, (int, float)) else None,
    host.get("median_windows_minus_linux_ms"),
    host.get("max_transport_uncertainty_ms"),
)
check3 = bool(
    check2
    and isinstance(sntp_offset, (int, float))
    and classification.get("classification") != "INCONCLUSIVE"
)
result["checks"]["check_3_live_cross_clock"] = {
    "pass": check3,
    "fresh_a19c_clock": clock,
    "a19c_returncode": clock_validation.get("returncode"),
    "windows_time_status": w32tm_status,
    "windows_time_source": w32tm_source,
    "windows_time_peers": w32tm_peers,
    "classification": classification,
}

result["diagnosis"] = classification
result["status"] = "PASS_DIAGNOSTIC" if check1 and check2 and check3 else "BLOCKED_DIAGNOSTIC"
result["next_gate"] = {
    "WSL_GUEST_DRIFT_FROM_WINDOWS_HOST": "WSL_CLOCK_RESYNC_REQUIRES_EXPLICIT_SYSTEM_ACTION",
    "WINDOWS_HOST_AND_WSL_SHARE_EXTERNAL_OFFSET": "WINDOWS_TIME_RESYNC_REQUIRES_EXPLICIT_SYSTEM_ACTION",
    "MULTI_CLOCK_MISMATCH": "CLOCK_TRANSPORT_DIAGNOSIS_REQUIRES_MORE_EVIDENCE",
    "CLOCK_WITHIN_RESEARCH_GATE": "RERUN_A19C_AND_A19B_V2_QUEUE_GATE",
}.get(classification.get("classification"), "FIX_CLOCK_DIAGNOSTIC")
result["terminal_for_current_authorization"] = result["next_gate"].endswith("EXPLICIT_SYSTEM_ACTION")

print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if result["status"] == "PASS_DIAGNOSTIC" else 1)
