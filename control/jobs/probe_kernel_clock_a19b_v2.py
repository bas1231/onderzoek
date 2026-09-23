#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

ROOT = Path.cwd()
SRC = ROOT / "control/weather/kernel_clock_probe_a19b_v2.c"


def run(*args: str, timeout: int = 15) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)


result: dict[str, object] = {
    "task": "WX-A19B-V2-KERNEL-CLOCK-PROBE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
    "changes_system_clock": False,
    "probe_semantics": "Linux adjtimex() with modes=0; read-only kernel NTP discipline inspection",
}

cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
if not cc:
    result.update({"status": "BLOCKED", "reason": "NO_C_COMPILER"})
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(2)
if not SRC.is_file():
    result.update({"status": "BLOCKED", "reason": "CLOCK_PROBE_SOURCE_MISSING"})
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(3)

with tempfile.TemporaryDirectory(prefix="a19b-clock-probe-") as td:
    binary = Path(td) / "clock_probe"
    build = run(cc, "-std=c11", "-Wall", "-Wextra", "-Werror", str(SRC), "-o", str(binary), timeout=30)
    result["build"] = {
        "compiler": cc,
        "returncode": build.returncode,
        "stdout": build.stdout[-2000:],
        "stderr": build.stderr[-4000:],
    }
    if build.returncode != 0:
        result.update({"status": "BLOCKED", "reason": "CLOCK_PROBE_COMPILE_FAILED"})
        print(json.dumps(result, indent=2, sort_keys=True))
        raise SystemExit(4)

    samples: list[dict[str, object]] = []
    for index in range(5):
        cp = run(str(binary), timeout=5)
        sample: dict[str, object] = {
            "sample_index": index,
            "returncode": cp.returncode,
            "stderr": cp.stderr[-2000:],
        }
        if cp.returncode == 0:
            try:
                parsed = json.loads(cp.stdout)
                if isinstance(parsed, dict):
                    sample["probe"] = parsed
                else:
                    sample["parse_error"] = "NON_OBJECT_JSON"
            except Exception as exc:
                sample["parse_error"] = type(exc).__name__
                sample["stdout"] = cp.stdout[-2000:]
        samples.append(sample)
        if index < 4:
            time.sleep(0.2)

result["samples"] = samples
valid = [s.get("probe") for s in samples if s.get("returncode") == 0 and isinstance(s.get("probe"), dict)]
result["valid_sample_count"] = len(valid)

# Supplemental OS status only; never substitutes for the kernel error fields.
if shutil.which("timedatectl"):
    td = run("timedatectl", "show", "-p", "NTPSynchronized", "--value", timeout=5)
    result["timedatectl_ntp_synchronized"] = td.stdout.strip() if td.returncode == 0 else None
else:
    result["timedatectl_ntp_synchronized"] = None

if len(valid) != 5:
    result.update({"status": "BLOCKED", "reason": "INCOMPLETE_KERNEL_CLOCK_SAMPLES"})
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(5)

result["observed"] = {
    "time_states": sorted({str(v.get("time_state_name")) for v in valid}),
    "sta_unsync_any": any(bool(v.get("sta_unsync")) for v in valid),
    "sta_clockerr_any": any(bool(v.get("sta_clockerr")) for v in valid),
    "offset_ms_min": min(float(v["offset_ms"]) for v in valid),
    "offset_ms_max": max(float(v["offset_ms"]) for v in valid),
    "maxerror_ms_min": min(float(v["maxerror_ms"]) for v in valid),
    "maxerror_ms_max": max(float(v["maxerror_ms"]) for v in valid),
    "esterror_ms_min": min(float(v["esterror_ms"]) for v in valid),
    "esterror_ms_max": max(float(v["esterror_ms"]) for v in valid),
}
result["status"] = "PROBE_COMPLETE"
result["decision"] = "NO_ELIGIBILITY_DECISION_IN_PROBE_STAGE"
print(json.dumps(result, indent=2, sort_keys=True))
