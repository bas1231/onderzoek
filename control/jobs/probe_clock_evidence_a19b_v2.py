#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
import subprocess


def run(*args: str) -> dict:
    try:
        cp = subprocess.run(args, text=True, capture_output=True, timeout=5)
        return {
            "returncode": cp.returncode,
            "stdout": cp.stdout,
            "stderr": cp.stderr,
        }
    except Exception as exc:
        return {
            "returncode": None,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
        }


def duration_ms(text: str) -> float | None:
    m = re.search(r"([-+]?\d+(?:\.\d+)?)\s*(ns|us|µs|ms|s)\b", text.strip(), re.I)
    if not m:
        return None
    value = float(m.group(1))
    unit = m.group(2).lower()
    scale = {
        "ns": 1e-6,
        "us": 1e-3,
        "µs": 1e-3,
        "ms": 1.0,
        "s": 1000.0,
    }[unit]
    return value * scale


def parse_timesync_status(text: str) -> dict:
    fields: dict[str, str] = {}
    for raw in text.splitlines():
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        fields[key.strip().lower()] = value.strip()

    offset_ms = duration_ms(fields.get("offset", ""))
    root_distance_ms = duration_ms(fields.get("root distance", ""))
    jitter_ms = duration_ms(fields.get("jitter", ""))

    stratum = None
    try:
        if fields.get("stratum") is not None:
            stratum = int(fields["stratum"])
    except ValueError:
        pass

    leap = fields.get("leap") or fields.get("leap status")
    uncertainty_ms = None
    if offset_ms is not None and root_distance_ms is not None:
        uncertainty_ms = abs(offset_ms) + abs(root_distance_ms) + abs(jitter_ms or 0.0)

    eligible_candidate = bool(
        uncertainty_ms is not None
        and uncertainty_ms <= 100.0
        and stratum is not None
        and 1 <= stratum <= 15
        and str(leap or "").strip().lower() in {"normal", "none"}
    )

    return {
        "fields": fields,
        "offset_ms": offset_ms,
        "root_distance_ms": root_distance_ms,
        "jitter_ms": jitter_ms,
        "stratum": stratum,
        "leap": leap,
        "conservative_uncertainty_ms": uncertainty_ms,
        "candidate_evidence_eligible": eligible_candidate,
        "candidate_semantics": "abs(offset)+root_distance+jitter; probe only, not yet accepted evidence source",
    }


result = {
    "task": "WEATHER-A19B-V2-CLOCK-EVIDENCE-PROBE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
    "timedatectl_present": bool(shutil.which("timedatectl")),
}

if not shutil.which("timedatectl"):
    result.update({
        "status": "BLOCKED",
        "next_gate": "NO_TIMEDATECTL",
    })
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0)

sync = run("timedatectl", "show", "-p", "NTPSynchronized", "--value")
status = run("timedatectl", "timesync-status")
result["ntp_sync"] = sync
result["timesync_status"] = status
result["parsed"] = parse_timesync_status(status.get("stdout", "")) if status.get("returncode") == 0 else {}

sync_raw = str(sync.get("stdout") or "").strip().lower()
ntp_synced = sync.get("returncode") == 0 and sync_raw == "yes"
candidate = bool((result.get("parsed") or {}).get("candidate_evidence_eligible"))

if ntp_synced and candidate:
    result["status"] = "CANDIDATE_CLOCK_SOURCE_AVAILABLE"
    result["next_gate"] = "REVIEW_AND_INTEGRATE_TIMEDATECTL_CLOCK_EVIDENCE"
elif ntp_synced:
    result["status"] = "SYNCED_BUT_NO_BOUNDED_OFFSET_EVIDENCE"
    result["next_gate"] = "BLOCKED_CLOCK_EVIDENCE"
else:
    result["status"] = "CLOCK_NOT_CONFIRMED_SYNCED"
    result["next_gate"] = "BLOCKED_CLOCK_EVIDENCE"

print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0)
