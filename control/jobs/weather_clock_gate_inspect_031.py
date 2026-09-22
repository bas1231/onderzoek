#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

ROOT = Path.home() / "prediction_research"
WX = Path.home() / "prediction_research_weather"
RESULT = ROOT / "control/results/WEATHER-CLOCK-GATE-028-INSPECT-030/RESULT.json"
WX_EVIDENCE = WX / "evidence/weather"


def safe_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def run_git(*args: str) -> dict:
    try:
        cp = subprocess.run(["git", *args], cwd=WX, text=True, capture_output=True, timeout=20)
        return {"returncode": cp.returncode, "stdout": cp.stdout.strip(), "stderr": cp.stderr.strip()}
    except Exception as exc:
        return {"returncode": 99, "stdout": "", "stderr": f"{type(exc).__name__}: {exc}"}

# CHECK 1/3: technical parser sanity.
synthetic = Path("/tmp/nonexistent-weather-clock-gate-031.json")
check1 = safe_json(synthetic) == {}

# CHECK 2/3: fail-closed on missing/corrupt sources.
check2 = True
try:
    assert safe_json(Path("/definitely/not/present/031.json")) == {}
except Exception:
    check2 = False

# CHECK 3/3: actual local source-of-truth inspection.
result_obj = safe_json(RESULT)
branch = run_git("branch", "--show-current")
head = run_git("rev-parse", "HEAD")
status = run_git("status", "--porcelain", "--untracked-files=no")

evidence_files = []
if WX_EVIDENCE.is_dir():
    for p in sorted(WX_EVIDENCE.glob("*.json"), key=lambda x: x.stat().st_mtime_ns, reverse=True)[:20]:
        obj = safe_json(p)
        evidence_files.append({
            "path": str(p),
            "status": obj.get("status"),
            "next_gate": obj.get("next_gate"),
            "generated_at": obj.get("generated_at"),
            "clock_readiness": obj.get("clock_readiness"),
            "queue_insertion_evidence_state": obj.get("queue_insertion_evidence_state"),
        })

check3 = bool(
    result_obj
    and branch.get("returncode") == 0
    and head.get("returncode") == 0
)

payload = {
    "task": "WEATHER-CLOCK-GATE-031-DIAGNOSTIC",
    "status": "PASS" if (check1 and check2 and check3) else "BLOCKED",
    "checks": {
        "check_1_technical": {"pass": check1},
        "check_2_fail_closed": {"pass": check2},
        "check_3_actual_local_state": {"pass": check3},
    },
    "source_result_path": str(RESULT),
    "source_result": result_obj,
    "weather_branch": branch,
    "weather_head": head,
    "weather_tracked_status": status,
    "recent_weather_evidence": evidence_files,
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
}

print(json.dumps(payload, indent=2, sort_keys=True))
raise SystemExit(0 if check1 and check2 and check3 else 2)
