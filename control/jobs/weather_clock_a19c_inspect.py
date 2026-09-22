#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

ROOT = Path.home() / "prediction_research_weather"


def cmd(*args: str) -> dict:
    cp = subprocess.run(args, cwd=ROOT if ROOT.is_dir() else None, text=True, capture_output=True, timeout=30)
    return {"returncode": cp.returncode, "stdout": cp.stdout[-12000:], "stderr": cp.stderr[-6000:]}

out: dict[str, object] = {
    "task": "WEATHER-CLOCK-A19C-INSPECT",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
}

if not ROOT.is_dir():
    out.update({"status": "BLOCKED", "reason": "WEATHER_WORKTREE_MISSING"})
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(2)

out["git"] = {
    "branch": cmd("git", "branch", "--show-current"),
    "head": cmd("git", "rev-parse", "HEAD"),
    "status_tracked": cmd("git", "status", "--porcelain", "--untracked-files=no"),
}

paths = []
for base in (ROOT / "control/jobs", ROOT / "control/weather", ROOT / "evidence/weather"):
    if base.is_dir():
        for p in sorted(base.iterdir()):
            name = p.name.lower()
            if "a19c" in name or "clock" in name:
                paths.append(p)

records = []
for p in paths:
    item = {"path": str(p.relative_to(ROOT)), "is_file": p.is_file()}
    if p.is_file():
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
            item["bytes"] = len(text.encode("utf-8", errors="replace"))
            item["content_tail"] = text[-16000:]
        except Exception as exc:
            item["read_error"] = f"{type(exc).__name__}: {exc}"
    records.append(item)

out["a19c_artifacts"] = records
out["clock_commands"] = {
    "chronyc_tracking": cmd("chronyc", "tracking", "-n") if subprocess.run(["sh", "-c", "command -v chronyc >/dev/null 2>&1"]).returncode == 0 else {"status": "NOT_INSTALLED"},
    "timedatectl_ntp": cmd("timedatectl", "show", "-p", "NTPSynchronized", "--value"),
}
out["status"] = "PASS"
print(json.dumps(out, indent=2, sort_keys=True))
