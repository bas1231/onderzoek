#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
TARGET_BRANCH = "ai/weather-madis-ldm-a19b"
TARGET_COMMIT = "81c0e37b56f38fbf589706560a043579a9e47c5d"
STATE = Path.home() / ".local" / "share" / "prediction-research"
WT_ROOT = STATE / "weather-worktrees"
WT = WT_ROOT / TARGET_COMMIT[:12]
PYTHON = ROOT / ".venv" / "bin" / "python"
if not PYTHON.is_file():
    PYTHON = Path(sys.executable)


def run(argv: list[str], *, cwd: Path = ROOT, timeout: int = 300) -> dict:
    try:
        cp = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, timeout=timeout)
        return {
            "argv": argv,
            "cwd": str(cwd),
            "returncode": cp.returncode,
            "stdout": cp.stdout[-20000:],
            "stderr": cp.stderr[-10000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "argv": argv,
            "cwd": str(cwd),
            "returncode": 124,
            "stdout": (exc.stdout or "")[-20000:] if isinstance(exc.stdout, str) else "",
            "stderr": ((exc.stderr or "") + "\nTIMEOUT")[-10000:] if isinstance(exc.stderr, str) else "TIMEOUT",
        }


def need_ok(label: str, result: dict, report: dict) -> None:
    report["steps"][label] = result
    if result.get("returncode") != 0:
        report["status"] = "FAILED"
        report["failed_step"] = label
        print(json.dumps(report, indent=2, sort_keys=True))
        raise SystemExit(1)


def main() -> int:
    report = {
        "task": "DEV-WEATHER-DEPLOY-E001",
        "target_branch": TARGET_BRANCH,
        "target_commit": TARGET_COMMIT,
        "worktree": str(WT),
        "python": str(PYTHON),
        "status": "RUNNING",
        "steps": {},
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
        "economic_conclusion": "NO_PROVEN_EDGE",
    }

    fetch = run(["git", "fetch", "origin", TARGET_BRANCH], timeout=120)
    need_ok("git_fetch_weather_branch", fetch, report)

    verify = run(["git", "rev-parse", "FETCH_HEAD"], timeout=30)
    need_ok("resolve_fetch_head", verify, report)
    fetched = verify["stdout"].strip().splitlines()[-1] if verify["stdout"].strip() else ""
    if fetched != TARGET_COMMIT:
        report["status"] = "FAILED"
        report["failed_step"] = "verify_target_commit"
        report["observed_commit"] = fetched
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1

    WT_ROOT.mkdir(parents=True, exist_ok=True)
    if WT.exists():
        wt_head = run(["git", "-C", str(WT), "rev-parse", "HEAD"], timeout=30)
        if wt_head.get("returncode") != 0 or wt_head.get("stdout", "").strip() != TARGET_COMMIT:
            report["status"] = "FAILED"
            report["failed_step"] = "existing_worktree_mismatch"
            report["existing_worktree_head"] = wt_head
            print(json.dumps(report, indent=2, sort_keys=True))
            return 1
        report["steps"]["worktree"] = {"returncode": 0, "status": "REUSED", "head": TARGET_COMMIT}
    else:
        add = run(["git", "worktree", "add", "--detach", str(WT), TARGET_COMMIT], timeout=60)
        need_ok("worktree", add, report)

    offline = run([str(PYTHON), "control/jobs/validate_public_metar_race.py", "--offline"], cwd=WT, timeout=120)
    need_ok("offline_three_gate_validation", offline, report)

    live = run([str(PYTHON), "control/jobs/validate_public_metar_race.py"], cwd=WT, timeout=180)
    need_ok("prospective_public_smoke", live, report)

    installer = run(["bash", "control/jobs/install_public_metar_race.sh"], cwd=WT, timeout=240)
    need_ok("install_and_start_user_services", installer, report)

    active = run(["systemctl", "--user", "is-active", "prediction-weather-public-metar-race.service"], cwd=WT, timeout=30)
    need_ok("collector_service_active", active, report)

    enabled = run(["systemctl", "--user", "is-enabled", "prediction-weather-public-metar-race.service"], cwd=WT, timeout=30)
    need_ok("collector_service_enabled", enabled, report)

    timer = run(["systemctl", "--user", "is-enabled", "prediction-weather-public-metar-analysis.timer"], cwd=WT, timeout=30)
    need_ok("analysis_timer_enabled", timer, report)

    # Give the long-running collector a chance to complete another cycle before
    # generating the final evidence summary.
    time.sleep(6)
    analysis = run([str(PYTHON), "control/weather/analyze_public_metar_race.py"], cwd=WT, timeout=60)
    need_ok("final_analysis", analysis, report)

    status = run([
        "systemctl", "--user", "--no-pager", "--full", "status",
        "prediction-weather-public-metar-race.service"
    ], cwd=WT, timeout=30)
    report["steps"]["service_status"] = status

    report["status"] = "PASS"
    report["deployed"] = True
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
