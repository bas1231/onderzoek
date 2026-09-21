#!/usr/bin/env python3
"""Three-gate validation for A19B-v2 queue-native LDM timing.

CHECK 1/3 technical: Python compile/unit tests + proven-fixture regression +
C syntax against a minimal interface stub matching the documented
pq_next()/queue_par_t contract.
CHECK 2/3 adversarial/fail-closed tests.
CHECK 3/3 realistic replay: immutable manifest-proven real NOAA A19A gzip is
framed, parsed, archived and decoded through the v2 path. Replay MUST remain
latency-ineligible.

A PASS here proves local source/readiness, not live LDM access and not edge.
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
A19A_MANIFESTS = STATE / "madis_omo_manifests"

sys.path.insert(0, str(WEATHER))
import madis_ldm_queue_native_a19b_v2 as q  # noqa: E402
from a19a_proven_replay_fixture import select_proven_a19a_gzip  # noqa: E402

PY = WEATHER / "madis_ldm_queue_native_a19b_v2.py"
C_READER = WEATHER / "madis_ldm_queue_reader_a19b_v2.c"
UNIT = WEATHER / "test_madis_ldm_queue_native_a19b_v2.py"
ADV = WEATHER / "test_madis_ldm_queue_native_a19b_v2_adversarial.py"
FIXTURE_HELPER = WEATHER / "a19a_proven_replay_fixture.py"
FIXTURE_TEST = WEATHER / "test_a19a_proven_replay_fixture.py"


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
unsigned pq_suspend(unsigned int);
#endif
'''
    with tempfile.TemporaryDirectory(prefix="a19b-v2-c-") as td:
        inc = Path(td) / "pq.h"
        inc.write_text(stub, encoding="utf-8")
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
        "scope": "syntax-only against documented minimal pq.h interface; not a real LDM ABI/link proof",
        "stdout": cp.stdout[-4000:],
        "stderr": cp.stderr[-4000:],
    }


def local_ldm_inventory() -> dict:
    commands = {name: shutil.which(name) for name in ("ldmd", "pqcheck", "pqcat", "pqact")}
    candidates = []
    for raw in (
        Path.home() / "ldm",
        Path("/usr/local/ldm"),
        Path("/opt/ldm"),
        Path("/home/ldm"),
    ):
        try:
            if raw.exists():
                candidates.append(str(raw))
        except OSError:
            pass
    queue_candidates = []
    for base in [Path(p) for p in candidates]:
        for rel in ("data/ldm.pq", "var/queues/ldm.pq", "data/queues/ldm.pq"):
            p = base / rel
            try:
                if p.is_file():
                    queue_candidates.append(str(p))
            except OSError:
                pass
    return {
        "commands": commands,
        "ldm_roots": candidates,
        "queue_candidates": sorted(set(queue_candidates)),
        "runtime_detected": bool(commands["ldmd"] or commands["pqcheck"] or candidates),
        "queue_detected": bool(queue_candidates),
    }


result = {
    "task": "WEATHER-MADIS-LDM-A19B-V2-THREE-CHECK-VALIDATION",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
    "checks": {},
}

# CHECK 1/3 — technical / regression.
try:
    for path in (PY, UNIT, ADV, FIXTURE_HELPER, FIXTURE_TEST):
        py_compile.compile(str(path), doraise=True)
    unit = run(sys.executable, str(UNIT), timeout=60)
    fixture_test = run(sys.executable, str(FIXTURE_TEST), timeout=60)
    ccheck = c_stub_compile()
    source = C_READER.read_text(encoding="utf-8")
    semantic_source_ok = all(token in source for token in (
        "PQ_READONLY",
        "pq_next(",
        "queue_par->inserted",
        "CLOCK_REALTIME",
        "CLOCK_MONOTONIC",
        "prod_par->info.sz",
    ))
    check1 = bool(
        unit.returncode == 0
        and "MADIS_LDM_QUEUE_NATIVE_A19B_V2_UNIT_TESTS_PASS" in unit.stdout
        and fixture_test.returncode == 0
        and "A19A_PROVEN_REPLAY_FIXTURE_TESTS_PASS" in fixture_test.stdout
        and ccheck.get("pass") is True
        and semantic_source_ok
    )
    result["checks"]["check_1_technical"] = {
        "pass": check1,
        "python_compile_pass": True,
        "unit_stdout": unit.stdout.strip(),
        "unit_stderr": unit.stderr[-3000:],
        "fixture_test_stdout": fixture_test.stdout.strip(),
        "fixture_test_stderr": fixture_test.stderr[-3000:],
        "c_source_contract_tokens_present": semantic_source_ok,
        "c_syntax_check": ccheck,
    }
except Exception as exc:
    check1 = False
    result["checks"]["check_1_technical"] = {
        "pass": False,
        "detail": f"{type(exc).__name__}: {exc}",
    }

# CHECK 2/3 — adversarial/fail-closed.
if check1:
    adv = run(sys.executable, str(ADV), timeout=60)
    check2 = bool(
        adv.returncode == 0
        and "MADIS_LDM_QUEUE_NATIVE_A19B_V2_ADVERSARIAL_TESTS_PASS" in adv.stdout
    )
    result["checks"]["check_2_fail_closed"] = {
        "pass": check2,
        "stdout": adv.stdout.strip(),
        "stderr": adv.stderr[-3000:],
    }
else:
    check2 = False
    result["checks"]["check_2_fail_closed"] = {"pass": False, "status": "SKIPPED_CHECK_1_FAILED"}

# CHECK 3/3 — manifest-proven real NOAA payload through framed replay.
fixture = select_proven_a19a_gzip(A19A_RAW, A19A_MANIFESTS)
source = Path(fixture["gzip_path"]) if fixture.get("status") == "PASS" else None

if check1 and check2 and source is not None:
    payload = source.read_bytes()
    # LDM queue insertion timestamps are timeval/microsecond precision. Align the
    # synthetic callback to the same boundary so the intended 10.000 ms replay
    # delta is deterministic.
    callback_ns = ((time.time_ns() - 5_000_000) // 1000) * 1000
    frame_raw = q.build_test_frame(
        payload,
        queue_insert_at_ns=callback_ns - 10_000_000,
        product_metadata_time_ns=callback_ns - 20_000_000,
        callback_realtime_ns=callback_ns,
        product_identifier="REPLAY-HF-ASOS-NOAA-MADIS",
        product_origin="A19A-REAL-NOAA-REPLAY",
    )
    with tempfile.NamedTemporaryFile(prefix="a19b-v2-replay-", suffix=".frame") as fh:
        fh.write(frame_raw)
        fh.flush()
        replay = run(sys.executable, str(PY), "--frame-file", fh.name, timeout=180)
    try:
        obj = json.loads(replay.stdout)
    except Exception:
        obj = {}
    decode = ((obj.get("decode") or {}).get("decode") or {})
    check3 = bool(
        replay.returncode == 0
        and obj.get("status") == "PASS"
        and obj.get("mode") == "replay"
        and decode.get("matched_station_count") == 5
        and float(decode.get("requested_station_coverage_fraction", 0)) == 1.0
        and obj.get("ldm_queue_insert_at_ns") is not None
        and obj.get("ldm_queue_insert_source") == "LDM_PQ_NEXT_QUEUE_PAR_T_INSERTED"
        and obj.get("eligible_for_queue_insertion_latency_analysis") is False
        and obj.get("eligible_for_adapter_first_seen_latency_analysis") is False
        and float(obj.get("queue_insert_to_reader_callback_ms")) == 10.0
    )
    result["checks"]["check_3_real_noaa_replay"] = {
        "pass": check3,
        "source": str(source),
        "fixture_provenance": fixture,
        "status": obj.get("status"),
        "matched_station_count": decode.get("matched_station_count"),
        "matched_stations": decode.get("matched_stations"),
        "station_coverage_fraction": decode.get("requested_station_coverage_fraction"),
        "ldm_queue_insert_at": obj.get("ldm_queue_insert_at"),
        "queue_insert_to_reader_callback_ms": obj.get("queue_insert_to_reader_callback_ms"),
        "queue_latency_eligible": obj.get("eligible_for_queue_insertion_latency_analysis"),
        "replay_semantics": "synthetic queue timestamp around a manifest-proven real NOAA payload; validates plumbing only, never latency evidence",
        "stderr": replay.stderr[-3000:],
    }
else:
    check3 = False
    result["checks"]["check_3_real_noaa_replay"] = {
        "pass": False,
        "status": "SKIPPED_NO_PROVEN_A19A_FIXTURE" if source is None else "SKIPPED_EARLIER_CHECK_FAILED",
        "fixture_provenance": fixture,
    }

all_pass = bool(check1 and check2 and check3)
clock = q.clock_health()
ldm = local_ldm_inventory()
result["clock_readiness"] = clock
result["ldm_runtime_inventory"] = ldm
result["status"] = "PASS_LOCAL_BUILD" if all_pass else "BLOCKED_LOCAL_VALIDATION"
result["a19b_v2_state"] = "SOURCE_AND_REPLAY_READY" if all_pass else "NOT_READY"

if not all_pass:
    next_gate = "FIX_A19B_V2_FAILED_CHECK"
elif clock.get("evidence_clock_eligible") is not True:
    next_gate = "BLOCKED_CLOCK_EVIDENCE"
elif not ldm.get("runtime_detected") or not ldm.get("queue_detected"):
    next_gate = "BLOCKED_NOAA_MADIS_LDM_ACCESS_OR_RUNTIME"
else:
    next_gate = "READY_FOR_REAL_QUEUE_NATIVE_CAPTURE"

result["next_gate"] = next_gate
result["queue_insertion_evidence_state"] = (
    "IMPLEMENTED_NOT_YET_PROSPECTIVELY_OBSERVED"
    if all_pass else
    "NOT_READY"
)
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if all_pass else 1)
