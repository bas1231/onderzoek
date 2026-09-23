#!/usr/bin/env python3
"""Three-gate validator for the public METAR source-race lane.

CHECK 1: compile + deterministic unit/regression tests.
CHECK 2: adversarial fail-closed tests.
CHECK 3: one prospective public-source smoke cycle followed by DB overlap proof.

No trading, account write, wallet action, paid API, or private MADIS access occurs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import py_compile
import sqlite3
import subprocess
import sys

ROOT = Path.cwd()
WEATHER = ROOT / "control" / "weather"
STATE = Path.home() / ".local" / "state" / "prediction-research"
DB = STATE / "weather_public_race.sqlite3"

FILES = [
    WEATHER / "public_metar_race.py",
    WEATHER / "analyze_public_metar_race.py",
    WEATHER / "test_public_metar_race.py",
    WEATHER / "test_public_metar_race_adversarial.py",
    WEATHER / "test_analyze_public_metar_race.py",
]


def run(*args: str, timeout: int = 120):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)


def overlap_summary(db: Path) -> dict:
    if not db.is_file():
        return {"pass": False, "reason": "DB_MISSING"}
    conn = sqlite3.connect(db)
    try:
        by_source = {
            row[0]: int(row[1])
            for row in conn.execute("SELECT source, COUNT(*) FROM observations GROUP BY source")
        }
        overlap = conn.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT station, obs_time_ns
                FROM observations
                WHERE source IN ('twc_kalshi','awc_api','nws_tgftp')
                GROUP BY station, obs_time_ns
                HAVING COUNT(DISTINCT source) >= 2
            )
            """
        ).fetchone()[0]
        candidate_twc_overlap = conn.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT station, obs_time_ns
                FROM observations
                WHERE source IN ('twc_kalshi','awc_api','nws_tgftp')
                GROUP BY station, obs_time_ns
                HAVING SUM(source='twc_kalshi') > 0
                   AND SUM(source IN ('awc_api','nws_tgftp')) > 0
            )
            """
        ).fetchone()[0]
        fetch_errors = conn.execute("SELECT COUNT(*) FROM fetches WHERE error IS NOT NULL").fetchone()[0]
        fetch_count = conn.execute("SELECT COUNT(*) FROM fetches").fetchone()[0]
    finally:
        conn.close()
    passed = bool(
        by_source.get("twc_kalshi", 0) > 0
        and (by_source.get("awc_api", 0) > 0 or by_source.get("nws_tgftp", 0) > 0)
        and candidate_twc_overlap > 0
    )
    return {
        "pass": passed,
        "rows_by_source": by_source,
        "cross_source_episode_count": int(overlap),
        "candidate_to_twc_overlap_count": int(candidate_twc_overlap),
        "fetch_count": int(fetch_count),
        "fetch_error_count": int(fetch_errors),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="skip prospective public HTTP smoke gate")
    ap.add_argument("--stations", default="", help="optional explicit ICAO list for live smoke")
    args = ap.parse_args()

    result = {
        "task": "WEATHER-PUBLIC-METAR-RACE-THREE-GATE",
        "checks": {},
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
        "private_madis_access": False,
        "economic_conclusion": "NO_PROVEN_EDGE",
    }

    # CHECK 1 — compile + deterministic tests.
    try:
        for path in FILES:
            py_compile.compile(str(path), doraise=True)
        unit = run(sys.executable, str(WEATHER / "test_public_metar_race.py"), timeout=60)
        analyzer = run(sys.executable, str(WEATHER / "test_analyze_public_metar_race.py"), timeout=60)
        check1 = bool(
            unit.returncode == 0
            and "PUBLIC_METAR_RACE_UNIT_TESTS_PASS" in unit.stdout
            and analyzer.returncode == 0
            and "PUBLIC_METAR_RACE_ANALYZER_TESTS_PASS" in analyzer.stdout
        )
        result["checks"]["check_1_technical"] = {
            "pass": check1,
            "compile_pass": True,
            "unit_stdout": unit.stdout.strip(),
            "unit_stderr": unit.stderr[-2000:],
            "analyzer_stdout": analyzer.stdout.strip(),
            "analyzer_stderr": analyzer.stderr[-2000:],
        }
    except Exception as exc:
        check1 = False
        result["checks"]["check_1_technical"] = {
            "pass": False,
            "compile_pass": False,
            "detail": f"{type(exc).__name__}: {exc}",
        }

    # CHECK 2 — fail closed under malformed timestamp/source data.
    if check1:
        adv = run(sys.executable, str(WEATHER / "test_public_metar_race_adversarial.py"), timeout=60)
        check2 = adv.returncode == 0 and "PUBLIC_METAR_RACE_ADVERSARIAL_TESTS_PASS" in adv.stdout
        result["checks"]["check_2_adversarial"] = {
            "pass": check2,
            "stdout": adv.stdout.strip(),
            "stderr": adv.stderr[-2000:],
        }
    else:
        check2 = False
        result["checks"]["check_2_adversarial"] = {"pass": False, "status": "SKIPPED_CHECK_1_FAILED"}

    # CHECK 3 — real prospective public fetch. This is source-timing evidence,
    # not historical replay and not an economic conclusion.
    if args.offline:
        check3 = True
        result["checks"]["check_3_prospective_public_smoke"] = {
            "pass": True,
            "status": "SKIPPED_BY_OFFLINE_FLAG",
            "eligible_for_source_lead_claim": False,
        }
    elif check1 and check2:
        cmd = [sys.executable, str(WEATHER / "public_metar_race.py"), "--once"]
        if args.stations:
            cmd.extend(["--stations", args.stations])
        live = run(*cmd, timeout=90)
        proof = overlap_summary(DB)
        check3 = bool(live.returncode == 0 and proof.get("pass"))
        result["checks"]["check_3_prospective_public_smoke"] = {
            "pass": check3,
            "runner_returncode": live.returncode,
            "stdout_tail": live.stdout[-5000:],
            "stderr_tail": live.stderr[-3000:],
            "db_proof": proof,
            "eligible_for_source_lead_claim": check3,
        }
    else:
        check3 = False
        result["checks"]["check_3_prospective_public_smoke"] = {
            "pass": False,
            "status": "SKIPPED_EARLIER_CHECK_FAILED",
        }

    all_pass = bool(check1 and check2 and check3)
    result["status"] = "PASS" if all_pass else "BLOCKED"
    result["next_gate"] = (
        "CONTINUOUS_PUBLIC_SOURCE_RACE_COLLECTION"
        if all_pass and not args.offline
        else "LIVE_SMOKE_REQUIRED" if all_pass and args.offline
        else "FIX_FAILED_CHECK"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
