#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

TASK_ID = "WEATHER-CLOCK-GATE-028"
roots = [
    Path.home() / "prediction_research",
    Path.home() / "prediction_research_weather",
]

candidates = []
for root in roots:
    for path in [
        root / "control" / "results" / TASK_ID / "RESULT.json",
        root / "evidence" / "weather" / f"{TASK_ID}.json",
        root / "evidence" / "weather" / "WEATHER-AWAY-A19B-latest.json",
    ]:
        if path.is_file():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                payload = {"parse_error": f"{type(exc).__name__}: {exc}"}
            candidates.append({"path": str(path), "payload": payload})

print(json.dumps({
    "task_id": TASK_ID,
    "status": "FOUND" if candidates else "NOT_FOUND",
    "candidates": candidates,
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
}, indent=2, sort_keys=True))
raise SystemExit(0 if candidates else 2)
