#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path.cwd()
TASK = "WEATHER-A19C2-TRANSPORT-RECOVER-029"
paths = {
    "result": ROOT / "control" / "results" / TASK / "RESULT.json",
    "lifecycle": ROOT / "control" / "lifecycle" / f"{TASK}.json",
}

out = {
    "task_id": TASK,
    "status": "DIAGNOSTIC",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
    "files": {},
}

for name, path in paths.items():
    if path.is_file():
        try:
            out["files"][name] = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            out["files"][name] = {"path": str(path), "read_error": f"{type(exc).__name__}: {exc}"}
    else:
        out["files"][name] = {"path": str(path), "missing": True}

hits = []
for base in (ROOT / "control" / "jobs", ROOT / "control" / "weather", ROOT / "experiments"):
    if not base.is_dir():
        continue
    for path in sorted(base.rglob("*")):
        if not path.is_file() or path.suffix not in {".py", ".json", ".md"}:
            continue
        text = ""
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        low = (path.name + "\n" + text[:20000]).lower()
        if "a19c2" in low or "transport-recover" in low or "transport_recover" in low:
            hits.append({
                "path": str(path.relative_to(ROOT)),
                "preview": text[:6000],
            })
        if len(hits) >= 12:
            break
    if len(hits) >= 12:
        break
out["a19c2_sources"] = hits

print(json.dumps(out, indent=2, sort_keys=True))
