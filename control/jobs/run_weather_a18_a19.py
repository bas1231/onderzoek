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

a18 = run(sys.executable, str(WEATHER / "e401_latency_a18.py"), timeout=240)
try:
    a18_obj = json.loads(a18.stdout)
except Exception:
    a18_obj = {}
result["a18_pass"] = a18.returncode == 0 and a18_obj.get("status") == "PASS"
result["a18"] = a18_obj
if not result["a18_pass"]:
    result["status"] = "BLOCKED_A18"
    result["a18_stderr"] = a18.stderr[-3000:]
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(12)

# Always test free public directory discovery first. This avoids confusing
# 5-minute/hourly file batching with LDM latency.
a19_index = run(sys.executable, str(WEATHER / "madis_omo_public_a19.py"), "--index-only", timeout=90)
try:
    a19_index_obj = json.loads(a19_index.stdout)
except Exception:
    a19_index_obj = {}
result["a19_index_pass"] = a19_index.returncode == 0
result["a19_index"] = a19_index_obj
if not result["a19_index_pass"]:
    result["status"] = "BLOCKED_A19_INDEX"
    result["a19_index_stderr"] = a19_index.stderr[-3000:]
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(13)

has_netcdf4 = importlib.util.find_spec("netCDF4") is not None
result["netcdf4_available"] = has_netcdf4
if has_netcdf4:
    a19_decode = run(sys.executable, str(WEATHER / "madis_omo_public_a19.py"), timeout=120)
    try:
        a19_decode_obj = json.loads(a19_decode.stdout)
    except Exception:
        a19_decode_obj = {}
    result["a19_decode_pass"] = a19_decode.returncode == 0 and (a19_decode_obj.get("decode") or {}).get("status") == "PASS"
    result["a19_decode"] = a19_decode_obj
else:
    result["a19_decode_pass"] = False
    result["a19_decode"] = {
        "status": "NOT_RUN_OPTIONAL_DEPENDENCY_MISSING",
        "dependency": "netCDF4",
        "install_hint": "~/prediction_research/.venv/bin/python -m pip install netCDF4",
    }

result["status"] = "PASS"
result["next_gate"] = (
    "A19A_DECODE_SCHEMA" if not result["a19_decode_pass"]
    else "A19B_LDM_PROSPECTIVE_RECEIPT_TIMING"
)
print(json.dumps(result, indent=2, sort_keys=True))
