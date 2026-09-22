#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
from datetime import datetime, timezone

ROOT = Path.home() / "prediction_research_weather"
PYTHON = Path.home() / "prediction_research/.venv/bin/python"


def run(*args: str, cwd: Path | None = None, timeout: int = 20) -> dict:
    try:
        cp = subprocess.run(
            args,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return {
            "command": list(args),
            "returncode": cp.returncode,
            "stdout": cp.stdout[-12000:],
            "stderr": cp.stderr[-6000:],
        }
    except Exception as exc:
        return {
            "command": list(args),
            "returncode": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def read_json(path: Path) -> dict:
    if not path.is_file():
        return {"exists": False, "path": str(path)}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return {"exists": True, "path": str(path), "json": obj}
    except Exception as exc:
        return {
            "exists": True,
            "path": str(path),
            "parse_error": f"{type(exc).__name__}: {exc}",
        }


out: dict = {
    "task": "WEATHER-A19B-V2-DIAG-SNAPSHOT",
    "captured_at": datetime.now(timezone.utc).isoformat(),
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
}

if not ROOT.is_dir():
    out["status"] = "BLOCKED_WEATHER_WORKTREE_MISSING"
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(2)

out["git"] = {
    "branch": run("git", "branch", "--show-current", cwd=ROOT),
    "head": run("git", "rev-parse", "HEAD", cwd=ROOT),
    "status": run("git", "status", "--porcelain=v1", cwd=ROOT),
    "log": run("git", "log", "-8", "--oneline", cwd=ROOT),
}

out["files"] = {
    "v1_report": read_json(ROOT / "evidence/weather/WEATHER-AWAY-A19B-latest.json"),
    "v2_validator_exists": (ROOT / "control/jobs/validate_madis_ldm_a19b_v2.py").is_file(),
    "v2_ingest_exists": (ROOT / "control/weather/madis_ldm_queue_ingest_a19b_v2.py").is_file(),
    "v2_reader_exists": (ROOT / "control/weather/madis_ldm_queue_reader_a19b_v2.c").is_file(),
}

if PYTHON.is_file() and (ROOT / "control/jobs/validate_madis_ldm_a19b_v2.py").is_file():
    out["v2_validator"] = run(
        str(PYTHON),
        "control/jobs/validate_madis_ldm_a19b_v2.py",
        cwd=ROOT,
        timeout=180,
    )
else:
    out["v2_validator"] = {"status": "NOT_RUN_MISSING_PYTHON_OR_VALIDATOR"}

clock: dict = {}
if shutil.which("chronyc"):
    clock["chronyc"] = run("chronyc", "tracking", "-n", cwd=ROOT, timeout=10)
else:
    clock["chronyc"] = {"status": "NOT_INSTALLED"}
if shutil.which("timedatectl"):
    clock["timedatectl"] = run(
        "timedatectl", "show", "-p", "NTPSynchronized", "--value",
        cwd=ROOT,
        timeout=10,
    )
else:
    clock["timedatectl"] = {"status": "NOT_AVAILABLE"}
out["clock"] = clock

out["ldm_runtime"] = {
    "pqcheck": shutil.which("pqcheck"),
    "pqact": shutil.which("pqact"),
    "ldmd": shutil.which("ldmd"),
    "ldmadmin": shutil.which("ldmadmin"),
    "gcc": shutil.which("gcc"),
    "pkg_config": shutil.which("pkg-config"),
}

out["status"] = "DIAG_CAPTURED"
print(json.dumps(out, indent=2, sort_keys=True))
