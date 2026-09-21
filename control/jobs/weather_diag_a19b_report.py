#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path.home() / "prediction_research_weather"
REPORT = ROOT / "evidence/weather/WEATHER-AWAY-A19B-latest.json"

out = {
    "task": "WEATHER-A19B-REPORT-DIAG",
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
}

if not REPORT.is_file():
    out.update({"status": "BLOCKED", "reason": "A19B_REPORT_MISSING", "report": str(REPORT)})
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(2)

try:
    obj = json.loads(REPORT.read_text(encoding="utf-8"))
except Exception as exc:
    out.update({"status": "BLOCKED", "reason": "A19B_REPORT_UNREADABLE", "detail": f"{type(exc).__name__}: {exc}"})
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(3)

v = (((obj.get("steps") or {}).get("a19b_three_gate_validation") or {}).get("parsed") or {})
checks = v.get("checks") or {}
out.update({
    "status": "PASS_DIAGNOSTIC",
    "report_status": obj.get("status"),
    "report_next_gate": obj.get("next_gate"),
    "validation_status": v.get("status"),
    "validation_next_gate": v.get("next_gate"),
    "a19b_v1_state": v.get("a19b_v1_state"),
    "queue_insertion_evidence_state": v.get("queue_insertion_evidence_state"),
    "checks": checks,
    "failed_checks": [name for name, value in checks.items() if isinstance(value, dict) and value.get("pass") is False],
    "report": str(REPORT),
})
print(json.dumps(out, indent=2, sort_keys=True))
