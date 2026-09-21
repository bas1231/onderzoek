#!/usr/bin/env python3
"""Validate and run E401 A17 point-in-time synchronization."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import py_compile
import subprocess
import sys

ROOT = Path.cwd()
WEATHER = ROOT / "control" / "weather"
sys.path.insert(0, str(WEATHER))

MODULE = WEATHER / "e401_sync_linker.py"
TEST = WEATHER / "test_e401_sync_linker.py"

for path in (MODULE, TEST):
    py_compile.compile(str(path), doraise=True)

test_run = subprocess.run(
    [sys.executable, str(TEST)],
    cwd=ROOT,
    text=True,
    capture_output=True,
    timeout=60,
)

result = {
    "task": "EDGE-HUNTER-KWI-SYNC-LINK-E401A17",
    "tests_pass": test_run.returncode == 0,
    "test_stdout": test_run.stdout.strip(),
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
}

if test_run.returncode != 0:
    result["status"] = "BLOCKED_TEST_FAILURE"
    result["test_stderr"] = test_run.stderr[-2000:]
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(10)

from e401_sync_linker import REPORTS, build_report
from summarize_kwi_market_reaction_e401 import summarize_reports

report = build_report(30000)
REPORTS.mkdir(parents=True, exist_ok=True)
report_path = REPORTS / "e401-a17-latest.json"
report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
summary = summarize_reports([report])

result.update({
    "status": "PASS",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "report": str(report_path),
    "primary_events_total": report.get("primary_events_total", 0),
    "pending_primary_events_total": report.get("pending_primary_events_total", 0),
    "revision_events_total": report.get("revision_events_total", 0),
    "evaluable_primary_events": report.get("evaluable_primary_events", 0),
    "evaluable_cities": report.get("evaluable_cities", []),
    "valid_synchronized_capture_fraction": report.get("valid_synchronized_capture_fraction", 0.0),
    "minimum_evidence_met": summary.get("minimum_evidence_met", False),
    "gate_checks": summary.get("checks", {}),
    "unique_primary_events": summary.get("unique_primary_events", 0),
    "unproven_primary_events": summary.get("unproven_primary_events", 0),
    "reaction_observed_count": summary.get("reaction_observed_count", 0),
    "no_reaction_observed_count": summary.get("no_reaction_observed_count", 0),
    "next_gate": summary.get("next_gate"),
})
print(json.dumps(result, indent=2, sort_keys=True))
