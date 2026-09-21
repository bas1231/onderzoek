#!/usr/bin/env python3
"""Three-gate validation for Weather A19B.

CHECK 1/3 technical: compile + unit/regression suite.
CHECK 2/3 fail-closed: adversarial suite.
CHECK 3/3 end-to-end replay: latest immutable A19A NOAA OMO gzip through A19B.

Replay is deliberately required to remain ineligible for live latency evidence.
No LDM application, feed activation, trading, wallet, or paid action occurs.
"""
from __future__ import annotations

import json
from pathlib import Path
import py_compile
import subprocess
import sys

ROOT = Path.cwd()
WEATHER = ROOT / "control" / "weather"
STATE = Path.home() / ".local" / "state" / "prediction-research"
A19A_RAW = STATE / "raw" / "madis_omo_public"

FILES = [
    WEATHER / "madis_ldm_ingest_a19b.py",
    WEATHER / "test_madis_ldm_a19b.py",
    WEATHER / "test_madis_ldm_a19b_adversarial.py",
]


def run(*args, timeout=120):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)


result = {
    "task": "WEATHER-MADIS-LDM-A19B-THREE-CHECK-VALIDATION",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
    "checks": {},
}

# CHECK 1/3 — technical
try:
    for path in FILES:
        py_compile.compile(str(path), doraise=True)
    unit = run(sys.executable, str(WEATHER / "test_madis_ldm_a19b.py"), timeout=60)
    check1 = unit.returncode == 0 and "MADIS_LDM_A19B_UNIT_TESTS_PASS" in unit.stdout
    result["checks"]["check_1_technical"] = {
        "pass": check1,
        "compile_pass": True,
        "stdout": unit.stdout.strip(),
        "stderr": unit.stderr[-2000:],
    }
except Exception as exc:
    result["checks"]["check_1_technical"] = {
        "pass": False,
        "compile_pass": False,
        "detail": f"{type(exc).__name__}: {exc}",
    }
    check1 = False

# CHECK 2/3 — adversarial/fail-closed
if check1:
    adv = run(sys.executable, str(WEATHER / "test_madis_ldm_a19b_adversarial.py"), timeout=60)
    check2 = adv.returncode == 0 and "MADIS_LDM_A19B_ADVERSARIAL_TESTS_PASS" in adv.stdout
    result["checks"]["check_2_fail_closed"] = {
        "pass": check2,
        "stdout": adv.stdout.strip(),
        "stderr": adv.stderr[-2000:],
    }
else:
    check2 = False
    result["checks"]["check_2_fail_closed"] = {"pass": False, "status": "SKIPPED_CHECK_1_FAILED"}

# CHECK 3/3 — real NOAA A19A replay through complete decoder path
latest = None
if A19A_RAW.is_dir():
    files = sorted(A19A_RAW.glob("*.gz"), key=lambda p: p.stat().st_mtime_ns)
    if files:
        latest = files[-1]

if check1 and check2 and latest is not None:
    replay = run(
        sys.executable,
        str(WEATHER / "madis_ldm_ingest_a19b.py"),
        "--file",
        str(latest),
        timeout=120,
    )
    try:
        obj = json.loads(replay.stdout)
    except Exception:
        obj = {}
    decode = ((obj.get("decode") or {}).get("decode") or {})
    forbidden_receipt_keys = [k for k in obj if "receipt" in str(k).lower()]
    check3 = bool(
        replay.returncode == 0
        and obj.get("status") == "PASS"
        and obj.get("mode") == "replay"
        and decode.get("matched_station_count") == 5
        and float(decode.get("requested_station_coverage_fraction", 0)) == 1.0
        and obj.get("ldm_queue_insert_at_ns") is None
        and obj.get("eligible_for_adapter_first_seen_latency_analysis") is False
        and obj.get("eligible_for_queue_insertion_latency_analysis") is False
        and obj.get("adapter_first_seen_at_ns") is not None
        and obj.get("decode_complete_at_ns") is not None
        and not forbidden_receipt_keys
    )
    result["checks"]["check_3_end_to_end_replay"] = {
        "pass": check3,
        "source": str(latest),
        "status": obj.get("status"),
        "matched_station_count": decode.get("matched_station_count"),
        "matched_stations": decode.get("matched_stations"),
        "station_coverage_fraction": decode.get("requested_station_coverage_fraction"),
        "adapter_first_seen_at": obj.get("adapter_first_seen_at"),
        "decode_complete_at": obj.get("decode_complete_at"),
        "ldm_queue_insert_at": obj.get("ldm_queue_insert_at"),
        "adapter_latency_eligible": obj.get("eligible_for_adapter_first_seen_latency_analysis"),
        "queue_latency_eligible": obj.get("eligible_for_queue_insertion_latency_analysis"),
        "clock_health": obj.get("clock_health"),
        "forbidden_receipt_keys": forbidden_receipt_keys,
        "stderr": replay.stderr[-2000:],
    }
else:
    check3 = False
    result["checks"]["check_3_end_to_end_replay"] = {
        "pass": False,
        "status": "SKIPPED_NO_A19A_GZIP" if latest is None else "SKIPPED_EARLIER_CHECK_FAILED",
    }

all_pass = bool(check1 and check2 and check3)
result["status"] = "PASS" if all_pass else "BLOCKED"
result["a19b_v1_state"] = "TECHNICALLY_READY_NOT_LDM_CONNECTED" if all_pass else "NOT_READY"
result["queue_insertion_evidence_state"] = "NOT_IMPLEMENTED_A19B_V1"
result["next_gate"] = "NOAA_MADIS_LDM_ACCESS_AND_QUEUE_NATIVE_A19B_V2" if all_pass else "FIX_FAILED_CHECK"
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if all_pass else 1)
