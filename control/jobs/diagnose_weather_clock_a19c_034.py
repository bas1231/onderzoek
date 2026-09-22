#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
import subprocess

MAX_UNCERTAINTY_MS = 100.0


def run(*args: str, timeout: int = 8) -> dict:
    try:
        cp = subprocess.run(args, text=True, capture_output=True, timeout=timeout)
        return {
            "returncode": cp.returncode,
            "stdout": cp.stdout,
            "stderr": cp.stderr,
        }
    except Exception as exc:
        return {
            "returncode": 125,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
        }


def seconds_value(text: str) -> float | None:
    m = re.search(r"([-+]?\d+(?:\.\d+)?)\s+seconds?", text)
    return float(m.group(1)) if m else None


def parse_tracking(text: str) -> dict:
    fields = {}
    for line in text.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip().lower()] = value.strip()

    system_line = fields.get("system time", "")
    system_s = seconds_value(system_line)
    if system_s is not None:
        lower = system_line.lower()
        if "slow of" in lower:
            system_s = -abs(system_s)
        elif "fast of" in lower:
            system_s = abs(system_s)

    root_delay_s = seconds_value(fields.get("root delay", ""))
    root_disp_s = seconds_value(fields.get("root dispersion", ""))
    leap = fields.get("leap status")
    ref_id = fields.get("reference id")

    try:
        stratum = int(fields["stratum"])
    except Exception:
        stratum = None

    system_ms = None if system_s is None else system_s * 1000.0
    delay_ms = None if root_delay_s is None else root_delay_s * 1000.0
    dispersion_ms = None if root_disp_s is None else root_disp_s * 1000.0

    uncertainty_ms = None
    if system_ms is not None and delay_ms is not None and dispersion_ms is not None:
        uncertainty_ms = abs(system_ms) + dispersion_ms + abs(delay_ms) / 2.0

    eligible = bool(
        str(leap or "").strip().lower() == "normal"
        and stratum is not None
        and 1 <= stratum <= 15
        and uncertainty_ms is not None
        and uncertainty_ms <= MAX_UNCERTAINTY_MS
    )

    return {
        "clock_source": f"chrony:{ref_id}" if ref_id else "chrony",
        "clock_offset_ms": system_ms,
        "clock_uncertainty_ms": uncertainty_ms,
        "clock_uncertainty_semantics": "abs(system_offset)+root_dispersion+root_delay/2",
        "root_delay_ms": delay_ms,
        "root_dispersion_ms": dispersion_ms,
        "stratum": stratum,
        "leap_status": leap,
        "evidence_clock_eligible": eligible,
    }


def parser_self_test() -> dict:
    sample = """Reference ID    : 1.2.3.4
Stratum         : 3
System time     : 0.000250 seconds slow of NTP time
Root delay      : 0.010000 seconds
Root dispersion : 0.002000 seconds
Leap status     : Normal
"""
    out = parse_tracking(sample)
    ok = bool(
        out["clock_offset_ms"] == -0.25
        and round(out["clock_uncertainty_ms"], 6) == 7.25
        and out["evidence_clock_eligible"] is True
    )
    return {"pass": ok, "parsed": out}


def timedatectl_sync() -> dict:
    if not shutil.which("timedatectl"):
        return {"available": False, "ntp_synchronized": None}
    cp = run("timedatectl", "show", "-p", "NTPSynchronized", "--value")
    raw = cp["stdout"].strip().lower()
    synced = True if raw == "yes" else False if raw == "no" else None
    return {
        "available": True,
        "returncode": cp["returncode"],
        "ntp_synchronized": synced,
        "raw": raw,
        "stderr": cp["stderr"][-1000:],
    }


result = {
    "task": "WEATHER-CLOCK-A19C-DIAG-034",
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "checks": {},
}

# CHECK 1/3: parser/semantic regression
check1 = parser_self_test()
result["checks"]["check_1_parser_semantics"] = check1

# CHECK 2/3: live inventory, read-only
chronyc = shutil.which("chronyc")
td = timedatectl_sync()
if chronyc:
    tracking = run("chronyc", "tracking", "-n")
    parsed = parse_tracking(tracking["stdout"]) if tracking["returncode"] == 0 else {}
    check2_pass = tracking["returncode"] == 0 and bool(tracking["stdout"].strip())
    result["checks"]["check_2_live_inventory"] = {
        "pass": check2_pass,
        "chronyc_path": chronyc,
        "chronyc_returncode": tracking["returncode"],
        "chronyc_stderr": tracking["stderr"][-1000:],
        "tracking": parsed,
        "timedatectl": td,
    }
else:
    parsed = {}
    check2_pass = False
    result["checks"]["check_2_live_inventory"] = {
        "pass": False,
        "chronyc_path": None,
        "reason": "CHRONYC_NOT_INSTALLED_OR_NOT_ON_PATH",
        "timedatectl": td,
    }

# CHECK 3/3: evidence consistency / fail-closed
clock_eligible = parsed.get("evidence_clock_eligible") is True
ntp_claim = td.get("ntp_synchronized")
consistent = bool(clock_eligible and (ntp_claim is not False))
result["checks"]["check_3_evidence_gate"] = {
    "pass": consistent,
    "clock_eligible": clock_eligible,
    "timedatectl_ntp_synchronized": ntp_claim,
    "max_uncertainty_ms": MAX_UNCERTAINTY_MS,
}

if not check1["pass"]:
    status = "BLOCKED_PARSER_REGRESSION"
    next_gate = "FIX_CLOCK_DIAGNOSTIC"
elif not chronyc:
    status = "BLOCKED_CHRONY_MISSING"
    next_gate = "CLOCK_EVIDENCE_RUNTIME_SETUP_REQUIRED"
elif not check2_pass:
    status = "BLOCKED_CHRONY_RUNTIME"
    next_gate = "FIX_OR_START_CLOCK_EVIDENCE_RUNTIME"
elif not consistent:
    status = "BLOCKED_CLOCK_UNCERTAINTY"
    next_gate = "IMPROVE_CLOCK_EVIDENCE"
else:
    status = "PASS_CLOCK_EVIDENCE"
    next_gate = "A19B_V2_QUEUE_NATIVE_PROSPECTIVE_CAPTURE"

result["status"] = status
result["next_gate"] = next_gate
result["terminal_for_current_authorization"] = status.startswith("BLOCKED_")

print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if status in {"PASS_CLOCK_EVIDENCE", "BLOCKED_CHRONY_MISSING", "BLOCKED_CHRONY_RUNTIME", "BLOCKED_CLOCK_UNCERTAINTY"} else 1)
