#!/usr/bin/env python3
"""Validate/run Weather A18 latency and A19A MADIS public feasibility."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import py_compile
import subprocess
import sys

ROOT = Path.cwd()
WEATHER = ROOT / "control" / "weather"
FILES = [
    WEATHER / "e401_latency_a18.py",
    WEATHER / "test_e401_latency_a18.py",
    WEATHER / "madis_omo_public_a19.py",
    WEATHER / "test_madis_omo_public_a19.py",
]


def run(*args, timeout=180):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)


def run_json(*args, timeout=180):
    try:
        proc = run(*args, timeout=timeout)
        try:
            obj = json.loads(proc.stdout)
        except Exception:
            obj = {}
        return {
            "timed_out": False,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "obj": obj,
        }
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return {
            "timed_out": True,
            "timeout_seconds": timeout,
            "returncode": None,
            "stdout": stdout,
            "stderr": stderr,
            "obj": {},
        }


result = {
    "task": "WEATHER-E401-A18-MADIS-A19-VALIDATION",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
}

try:
    for path in FILES:
        py_compile.compile(str(path), doraise=True)
    result["compile_pass"] = True
except Exception as exc:
    result.update({"compile_pass": False, "status": "BLOCKED_COMPILE", "detail": f"{type(exc).__name__}: {exc}"})
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(10)

lat_test = run(sys.executable, str(WEATHER / "test_e401_latency_a18.py"), timeout=60)
madis_test = run(sys.executable, str(WEATHER / "test_madis_omo_public_a19.py"), timeout=60)
result["a18_tests_pass"] = lat_test.returncode == 0
result["a18_test_stdout"] = lat_test.stdout.strip()
result["a19_tests_pass"] = madis_test.returncode == 0
result["a19_test_stdout"] = madis_test.stdout.strip()
if not result["a18_tests_pass"] or not result["a19_tests_pass"]:
    result["status"] = "BLOCKED_TEST_FAILURE"
    result["test_stderr"] = (lat_test.stderr + "\n" + madis_test.stderr)[-3000:]
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(11)

# A18 and A19 are independent evidence lanes. A timeout in one must not erase
# evidence from the other; overall status still fails closed if either blocks.
a18_run = run_json(sys.executable, str(WEATHER / "e401_latency_a18.py"), timeout=240)
a18_obj = a18_run["obj"]
result["a18_timed_out"] = a18_run["timed_out"]
result["a18_pass"] = (not a18_run["timed_out"] and a18_run["returncode"] == 0 and a18_obj.get("status") == "PASS")
result["a18"] = a18_obj
if a18_run["timed_out"]:
    result["a18_blocker"] = f"TIMEOUT_AFTER_{a18_run['timeout_seconds']}S"
elif not result["a18_pass"]:
    result["a18_stderr"] = a18_run["stderr"][-3000:]

# Always test free public directory discovery even if A18 is blocked. This
# avoids coupling market-log performance to the independent MADIS feasibility.
a19_index_run = run_json(sys.executable, str(WEATHER / "madis_omo_public_a19.py"), "--index-only", timeout=90)
a19_index_obj = a19_index_run["obj"]
result["a19_index_timed_out"] = a19_index_run["timed_out"]
result["a19_index_pass"] = (not a19_index_run["timed_out"] and a19_index_run["returncode"] == 0)
result["a19_index"] = a19_index_obj
if not result["a19_index_pass"]:
    result["a19_index_stderr"] = a19_index_run["stderr"][-3000:]

has_netcdf4 = importlib.util.find_spec("netCDF4") is not None
result["netcdf4_available"] = has_netcdf4
if has_netcdf4 and result["a19_index_pass"]:
    a19_decode_run = run_json(sys.executable, str(WEATHER / "madis_omo_public_a19.py"), timeout=120)
    a19_decode_obj = a19_decode_run["obj"]
    result["a19_decode_timed_out"] = a19_decode_run["timed_out"]
    result["a19_decode_pass"] = (
        not a19_decode_run["timed_out"]
        and a19_decode_run["returncode"] == 0
        and (a19_decode_obj.get("decode") or {}).get("status") == "PASS"
    )
    result["a19_decode"] = a19_decode_obj
    if not result["a19_decode_pass"]:
        result["a19_decode_stderr"] = a19_decode_run["stderr"][-3000:]
else:
    result["a19_decode_timed_out"] = False
    result["a19_decode_pass"] = False
    result["a19_decode"] = {
        "status": "NOT_RUN_OPTIONAL_DEPENDENCY_MISSING" if not has_netcdf4 else "NOT_RUN_INDEX_BLOCKED",
        "dependency": "netCDF4" if not has_netcdf4 else None,
        "install_hint": "~/prediction_research/.venv/bin/python -m pip install netCDF4" if not has_netcdf4 else None,
    }

if result["a18_pass"] and result["a19_index_pass"] and result["a19_decode_pass"]:
    result["status"] = "PASS"
    result["next_gate"] = "A19B_LDM_PROSPECTIVE_RECEIPT_TIMING"
else:
    blockers = []
    if not result["a18_pass"]:
        blockers.append("A18")
    if not result["a19_index_pass"]:
        blockers.append("A19_INDEX")
    elif not result["a19_decode_pass"]:
        blockers.append("A19_DECODE")
    result["status"] = "PARTIAL_BLOCKED"
    result["blocked_lanes"] = blockers
    result["next_gate"] = "RESOLVE_BLOCKED_LANES"

print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if result["status"] == "PASS" else 12)
