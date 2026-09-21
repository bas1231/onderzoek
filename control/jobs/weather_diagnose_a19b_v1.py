#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

report = Path.home() / "prediction_research_weather/evidence/weather/WEATHER-AWAY-A19B-latest.json"

out = {
    "task": "WEATHER-DIAGNOSE-A19B-V1",
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
}

if not report.is_file():
    out.update({"status": "BLOCKED", "reason": "A19B_V1_REPORT_MISSING", "report": str(report)})
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(2)

try:
    obj = json.loads(report.read_text(encoding="utf-8"))
except Exception as exc:
    out.update({"status": "BLOCKED", "reason": "A19B_V1_REPORT_PARSE_FAILED", "detail": f"{type(exc).__name__}: {exc}"})
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(3)

validation = (((obj.get("steps") or {}).get("a19b_three_gate_validation") or {}).get("parsed") or {})
checks = validation.get("checks") or {}
out.update({
    "status": "PASS" if validation.get("status") == "PASS" else "FAILED",
    "report_status": obj.get("status"),
    "generated_at": obj.get("generated_at"),
    "validation_status": validation.get("status"),
    "a19b_v1_state": validation.get("a19b_v1_state"),
    "next_gate": validation.get("next_gate") or obj.get("next_gate"),
    "check_1_technical": checks.get("check_1_technical"),
    "check_2_fail_closed": checks.get("check_2_fail_closed"),
    "check_3_end_to_end_replay": checks.get("check_3_end_to_end_replay"),
    "clock_readiness": (obj.get("steps") or {}).get("clock_readiness"),
    "report": str(report),
})
print(json.dumps(out, indent=2, sort_keys=True))
raise SystemExit(0)
