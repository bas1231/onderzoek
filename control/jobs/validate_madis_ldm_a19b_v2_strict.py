#!/usr/bin/env python3
"""Strict three-gate validation for A19B-v2 queue-native LDM timing.

CHECK 1/3 technical:
- compile base + strict Python implementation and tests;
- base regression tests + strict regression tests;
- safe C-reader syntax check against documented pq_next() interface;
- prove the safe C reader doesn't access queue_par_t.is_locked.

CHECK 2/3 adversarial/fail-closed:
- existing malformed-frame tests;
- strict signature/flag/time provenance tests.

CHECK 3/3 realistic replay:
- latest real NOAA A19A gzip through strict queue-native frame/decode path;
- replay must remain latency-ineligible.

PASS_LOCAL_BUILD is not live LDM evidence and not an economic edge.
"""
from __future__ import annotations

import json
from pathlib import Path
import py_compile
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path.cwd()
WEATHER = ROOT / "control" / "weather"
STATE = Path.home() / ".local" / "state" / "prediction-research"
A19A_RAW = STATE / "raw" / "madis_omo_public"

sys.path.insert(0, str(WEATHER))
import madis_ldm_queue_native_a19b_v2_strict as q  # noqa: E402

BASE_PY = WEATHER / "madis_ldm_queue_native_a19b_v2.py"
STRICT_PY = WEATHER / "madis_ldm_queue_native_a19b_v2_strict.py"
C_READER = WEATHER / "madis_ldm_queue_reader_a19b_v2_safe.c"
BASE_UNIT = WEATHER / "test_madis_ldm_queue_native_a19b_v2.py"
STRICT_UNIT = WEATHER / "test_madis_ldm_queue_native_a19b_v2_strict.py"
BASE_ADV = WEATHER / "test_madis_ldm_queue_native_a19b_v2_adversarial.py"
STRICT_ADV = WEATHER / "test_madis_ldm_queue_native_a19b_v2_strict_adversarial.py"


def run(*args: str, timeout: int = 120, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=timeout)


def c_stub_compile() -> dict:
    cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if not cc:
        return {"pass": False, "status": "NO_C_COMPILER"}
    stub = r'''#ifndef PQ_H
#define PQ_H
#include <stdbool.h>
#include <stddef.h>
#include <sys/time.h>
#include <sys/types.h>
typedef struct timeval timestampt;
typedef unsigned char signaturet[16];
typedef unsigned int feedtypet;
typedef struct { timestampt arrival; signaturet signature; char *origin; feedtypet feedtype; unsigned int seqno; char *ident; unsigned int sz; } prod_info;
typedef struct { prod_info info; void *data; void *encoded; size_t size; } prod_par_t;
typedef struct { timestampt inserted; off_t offset; bool early_cursor; bool is_full; bool is_locked; } queue_par_t;
typedef struct pqueue pqueue;
typedef struct prod_class prod_class_t;
typedef void pq_next_func(const prod_par_t *restrict, const queue_par_t *restrict, void *restrict);
#define PQ_READONLY 0x02
#define PQ_END -1
#define PQ_CLASS_ALL ((const prod_class_t*)1)
int pq_open(const char*, int, pqueue**);
int pq_close(pqueue*);
void pq_cset(pqueue*, const timestampt*);
int pq_next(pqueue*, bool, const prod_class_t*, pq_next_func*, bool, void*);
int pq_suspend(unsigned int);
#endif
'''
    with tempfile.TemporaryDirectory(prefix="a19b-v2-strict-c-") as td:
        (Path(td) / "pq.h").write_text(stub, encoding="utf-8")
        cp = run(
            cc,
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-I",
            td,
            "-fsyntax-only",
            str(C_READER),
            timeout=60,
        )
    return {
        "pass": cp.returncode == 0,
        "compiler": cc,
        "scope": "syntax-only against documented minimal pq.h interface; not real LDM ABI/link proof",
        "stdout": cp.stdout[-4000:],
        "stderr": cp.stderr[-4000:],
    }


def local_ldm_inventory() -> dict:
    commands = {name: shutil.which(name) for name in ("ldmd", "pqcheck", "pqcat", "pqact")}
    roots: list[str] = []
    for raw in (
        Path.home() / "ldm",
        Path("/usr/local/ldm"),
        Path("/opt/ldm"),
        Path("/home/ldm"),
    ):
        try:
            if raw.exists():
                roots.append(str(raw))
        except OSError:
            pass
    queues: list[str] = []
    for base in map(Path, roots):
        for rel in ("data/ldm.pq", "var/queues/ldm.pq", "data/queues/ldm.pq"):
            p = base / rel
            try:
                if p.is_file():
                    queues.append(str(p))
            except OSError:
                pass
    return {
        "commands": commands,
        "ldm_roots": roots,
        "queue_candidates": sorted(set(queues)),
        "runtime_detected": bool(commands["ldmd"] or commands["pqcheck"] or roots),
        "queue_detected": bool(queues),
    }


result = {
    "task": "WEATHER-MADIS-LDM-A19B-V2-STRICT-THREE-CHECK-VALIDATION",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
    "checks": {},
}

# CHECK 1/3 — technical
try:
    for path in (BASE_PY, STRICT_PY, BASE_UNIT, STRICT_UNIT, BASE_ADV, STRICT_ADV):
        py_compile.compile(str(path), doraise=True)
    base_unit = run(sys.executable, str(BASE_UNIT), timeout=60)
    strict_unit = run(sys.executable, str(STRICT_UNIT), timeout=60)
    ccheck = c_stub_compile()
    csource = C_READER.read_text(encoding="utf-8")
    safe_source = bool(
        "PQ_READONLY" in csource
        and "pq_next(" in csource
        and "queue_par->inserted" in csource
        and "info->sz" in csource
        and "queue_par->is_locked" not in csource
    )
    check1 = bool(
        base_unit.returncode == 0
        and "MADIS_LDM_QUEUE_NATIVE_A19B_V2_UNIT_TESTS_PASS" in base_unit.stdout
        and strict_unit.returncode == 0
        and "MADIS_LDM_QUEUE_NATIVE_A19B_V2_STRICT_UNIT_TESTS_PASS" in strict_unit.stdout
        and ccheck.get("pass") is True
        and safe_source
    )
    result["checks"]["check_1_technical"] = {
        "pass": check1,
        "python_compile_pass": True,
        "base_unit_stdout": base_unit.stdout.strip(),
        "base_unit_stderr": base_unit.stderr[-3000:],
        "strict_unit_stdout": strict_unit.stdout.strip(),
        "strict_unit_stderr": strict_unit.stderr[-3000:],
        "safe_c_source_contract": safe_source,
        "c_syntax_check": ccheck,
    }
except Exception as exc:
    check1 = False
    result["checks"]["check_1_technical"] = {
        "pass": False,
        "detail": f"{type(exc).__name__}: {exc}",
    }

# CHECK 2/3 — adversarial/fail-closed
if check1:
    base_adv = run(sys.executable, str(BASE_ADV), timeout=60)
    strict_adv = run(sys.executable, str(STRICT_ADV), timeout=60)
    check2 = bool(
        base_adv.returncode == 0
        and "MADIS_LDM_QUEUE_NATIVE_A19B_V2_ADVERSARIAL_TESTS_PASS" in base_adv.stdout
        and strict_adv.returncode == 0
        and "MADIS_LDM_QUEUE_NATIVE_A19B_V2_STRICT_ADVERSARIAL_TESTS_PASS" in strict_adv.stdout
    )
    result["checks"]["check_2_fail_closed"] = {
        "pass": check2,
        "base_stdout": base_adv.stdout.strip(),
        "base_stderr": base_adv.stderr[-3000:],
        "strict_stdout": strict_adv.stdout.strip(),
        "strict_stderr": strict_adv.stderr[-3000:],
    }
else:
    check2 = False
    result["checks"]["check_2_fail_closed"] = {"pass": False, "status": "SKIPPED_CHECK_1_FAILED"}

# CHECK 3/3 — real NOAA payload, synthetic queue timestamps, strict replay semantics
latest = None
if A19A_RAW.is_dir():
    files = sorted(A19A_RAW.glob("*.gz"), key=lambda p: p.stat().st_mtime_ns)
    if files:
        latest = files[-1]

if check1 and check2 and latest is not None:
    payload = latest.read_bytes()
    callback_ns = time.time_ns() - 5_000_000
    frame_raw = q.build_test_frame(
        payload,
        queue_insert_at_ns=callback_ns - 10_000_000,
        product_metadata_time_ns=callback_ns - 20_000_000,
        callback_realtime_ns=callback_ns,
        product_identifier="REPLAY-HF-ASOS-NOAA-MADIS",
        product_origin="A19A-REAL-NOAA-STRICT-REPLAY",
    )
    with tempfile.NamedTemporaryFile(prefix="a19b-v2-strict-replay-", suffix=".frame") as fh:
        fh.write(frame_raw)
        fh.flush()
        replay = run(sys.executable, str(STRICT_PY), "--frame-file", fh.name, timeout=180)
    try:
        obj = json.loads(replay.stdout)
    except Exception:
        obj = {}
    decode = ((obj.get("decode") or {}).get("decode") or {})
    strict_gate = obj.get("strict_provenance_gate") or {}
    check3 = bool(
        replay.returncode == 0
        and obj.get("status") == "PASS"
        and obj.get("mode") == "replay"
        and decode.get("matched_station_count") == 5
        and float(decode.get("requested_station_coverage_fraction", 0)) == 1.0
        and obj.get("ldm_queue_insert_source") == "LDM_PQ_NEXT_QUEUE_PAR_T_INSERTED"
        and float(obj.get("queue_insert_to_reader_callback_ms")) == 10.0
        and obj.get("eligible_for_queue_insertion_latency_analysis") is False
        and obj.get("eligible_for_adapter_first_seen_latency_analysis") is False
        and strict_gate.get("ldm_signature_matches_payload_md5") is True
        and strict_gate.get("known_safe_flags_only") is True
        and obj.get("queue_capture_gap_risk") is False
    )
    result["checks"]["check_3_real_noaa_replay"] = {
        "pass": check3,
        "source": str(latest),
        "status": obj.get("status"),
        "matched_station_count": decode.get("matched_station_count"),
        "matched_stations": decode.get("matched_stations"),
        "station_coverage_fraction": decode.get("requested_station_coverage_fraction"),
        "ldm_queue_insert_at": obj.get("ldm_queue_insert_at"),
        "queue_insert_to_reader_callback_ms": obj.get("queue_insert_to_reader_callback_ms"),
        "queue_latency_eligible": obj.get("eligible_for_queue_insertion_latency_analysis"),
        "strict_provenance_gate": strict_gate,
        "replay_semantics": "synthetic queue timestamps around real NOAA payload; plumbing proof only, never latency evidence",
        "stderr": replay.stderr[-3000:],
    }
else:
    check3 = False
    result["checks"]["check_3_real_noaa_replay"] = {
        "pass": False,
        "status": "SKIPPED_NO_A19A_GZIP" if latest is None else "SKIPPED_EARLIER_CHECK_FAILED",
    }

all_pass = bool(check1 and check2 and check3)
clock = q.clock_health()
ldm = local_ldm_inventory()
result["clock_readiness"] = clock
result["ldm_runtime_inventory"] = ldm
result["status"] = "PASS_LOCAL_BUILD" if all_pass else "BLOCKED_LOCAL_VALIDATION"
result["a19b_v2_state"] = "STRICT_SOURCE_AND_REPLAY_READY" if all_pass else "NOT_READY"
result["queue_insertion_evidence_state"] = (
    "IMPLEMENTED_NOT_YET_PROSPECTIVELY_OBSERVED" if all_pass else "NOT_READY"
)

if not all_pass:
    next_gate = "FIX_A19B_V2_STRICT_FAILED_CHECK"
elif clock.get("evidence_clock_eligible") is not True:
    next_gate = "BLOCKED_CLOCK_EVIDENCE"
elif not ldm.get("runtime_detected") or not ldm.get("queue_detected"):
    next_gate = "BLOCKED_NOAA_MADIS_LDM_ACCESS_OR_RUNTIME"
else:
    next_gate = "READY_FOR_REAL_QUEUE_NATIVE_CAPTURE"

result["next_gate"] = next_gate
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if all_pass else 1)
