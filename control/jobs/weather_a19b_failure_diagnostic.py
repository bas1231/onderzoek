#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

report = Path.home() / "prediction_research_weather/evidence/weather/WEATHER-AWAY-A19B-latest.json"

out = {
    "task": "WEATHER-A19B-FAILURE-DIAGNOSTIC",
    "report": str(report),
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
}

if not report.is_file():
    out.update({"status": "BLOCKED", "reason": "REPORT_MISSING"})
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(1)

try:
    obj = json.loads(report.read_text(encoding="utf-8"))
except Exception as exc:
    out.update({"status": "BLOCKED", "reason": "REPORT_PARSE_FAILED", "detail": f"{type(exc).__name__}: {exc}"})
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(1)

validation = (((obj.get("steps") or {}).get("a19b_three_gate_validation") or {}).get("parsed") or {})
out.update({
    "status": "PASS_DIAGNOSTIC",
    "report_status": obj.get("status"),
    "generated_at": obj.get("generated_at"),
    "validation_status": validation.get("status"),
    "a19b_v1_state": validation.get("a19b_v1_state"),
    "next_gate": validation.get("next_gate"),
    "checks": validation.get("checks"),
})
print(json.dumps(out, indent=2, sort_keys=True))
