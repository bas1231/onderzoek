#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path.home() / "prediction_research_weather"
PYTHON = Path.home() / "prediction_research/.venv/bin/python"
V1_REPORT = ROOT / "evidence/weather/WEATHER-AWAY-A19B-latest.json"
V2_VALIDATOR = ROOT / "control/jobs/validate_madis_ldm_a19b_v2.py"


def run(*args: str, cwd: Path | None = None, timeout: int = 120) -> dict:
    try:
        cp = subprocess.run(
            args,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return {
            "returncode": cp.returncode,
            "stdout": cp.stdout[-20000:],
            "stderr": cp.stderr[-10000:],
        }
    except Exception as exc:
        return {
            "returncode": 125,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
        }


out: dict = {
    "task": "WEATHER-A19B-CONTEXT-SNAPSHOT",
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
}

if not ROOT.is_dir():
    out.update({"status": "BLOCKED", "next_gate": "WEATHER_WORKTREE_MISSING"})
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(2)

out["git"] = {
    "branch": run("git", "branch", "--show-current", cwd=ROOT, timeout=30),
    "head": run("git", "rev-parse", "HEAD", cwd=ROOT, timeout=30),
    "status": run("git", "status", "--porcelain=v1", cwd=ROOT, timeout=30),
}

if V1_REPORT.is_file():
    try:
        out["a19b_v1_report"] = json.loads(V1_REPORT.read_text(encoding="utf-8"))
    except Exception as exc:
        out["a19b_v1_report"] = {"parse_error": f"{type(exc).__name__}: {exc}"}
else:
    out["a19b_v1_report"] = {"status": "MISSING"}

out["runtime_inventory"] = {
    "chronyc": shutil.which("chronyc"),
    "ldmd": shutil.which("ldmd"),
    "pqcheck": shutil.which("pqcheck"),
    "pqcat": shutil.which("pqcat"),
    "gcc": shutil.which("gcc"),
    "cc": shutil.which("cc"),
}

if shutil.which("chronyc"):
    out["clock"] = run("chronyc", "tracking", "-n", cwd=ROOT, timeout=10)
elif shutil.which("timedatectl"):
    out["clock"] = run(
        "timedatectl", "show", "-p", "NTPSynchronized", "--value",
        cwd=ROOT,
        timeout=10,
    )
else:
    out["clock"] = {"returncode": 127, "stdout": "", "stderr": "NO_CLOCK_TOOL"}

if V2_VALIDATOR.is_file() and PYTHON.is_file():
    v2 = run(str(PYTHON), str(V2_VALIDATOR.relative_to(ROOT)), cwd=ROOT, timeout=600)
    out["a19b_v2_validator"] = v2
    try:
        out["a19b_v2_parsed"] = json.loads(v2["stdout"])
    except Exception:
        out["a19b_v2_parsed"] = {}
else:
    out["a19b_v2_validator"] = {
        "returncode": 127,
        "stdout": "",
        "stderr": "V2_VALIDATOR_OR_PROJECT_PYTHON_MISSING",
    }
    out["a19b_v2_parsed"] = {}

v1_pass = bool(
    isinstance(out.get("a19b_v1_report"), dict)
    and out["a19b_v1_report"].get("status") == "PASS"
)
v2_obj = out.get("a19b_v2_parsed") or {}
v2_local_pass = v2_obj.get("status") == "PASS_LOCAL_BUILD"

if not v1_pass:
    out["status"] = "DIAGNOSIS_COMPLETE"
    out["next_gate"] = "A19B_V1_PROVENANCE_OR_VALIDATION_REPAIR"
elif not v2_local_pass:
    out["status"] = "DIAGNOSIS_COMPLETE"
    out["next_gate"] = v2_obj.get("next_gate") or "A19B_V2_LOCAL_BUILD_OR_VALIDATION"
else:
    out["status"] = "DIAGNOSIS_COMPLETE"
    out["next_gate"] = v2_obj.get("next_gate") or "A19B_V2_RUNTIME_GATE"

print(json.dumps(out, indent=2, sort_keys=True))
raise SystemExit(0)
