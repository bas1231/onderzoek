from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import os
import subprocess


ROOT = Path(__file__).resolve().parents[2]
TASK = "CONTROL-WORK-CADENCE-VERIFY-E008"
TIMER = "prediction-research-hourly-director.timer"
SERVICE = "prediction-research-hourly-director.service"


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        return f"<UNAVAILABLE {type(exc).__name__}: {exc}>"


def run(args: list[str], timeout: int = 15) -> dict[str, object]:
    try:
        proc = subprocess.run(
            args,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return {
            "rc": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
    except Exception as exc:
        return {
            "rc": None,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
        }


def safe_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "unavailable": True,
            "error": f"{type(exc).__name__}: {exc}",
            "path": str(path),
        }


def latest_hourly_runs(limit: int = 12) -> list[dict[str, object]]:
    rows = []
    for path in sorted(
        (ROOT / "knowledge/runs").glob("hourly-*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]:
        rows.append({
            "path": str(path.relative_to(ROOT)),
            "mtime_utc": datetime.fromtimestamp(
                path.stat().st_mtime,
                tz=timezone.utc,
            ).isoformat(),
            "size": path.stat().st_size,
        })
    return rows


def unit_show(unit: str, properties: list[str]) -> dict[str, object]:
    args = ["systemctl", "--user", "show", unit]
    for prop in properties:
        args.extend(["-p", prop])
    return run(args)


result = {
    "schema": "PVA_HOURLY_DIRECTOR_INCIDENT_DIAG_V1",
    "observed_at_utc": datetime.now(timezone.utc).isoformat(),
    "e008": {
        "result_json": read(ROOT / "control/results" / TASK / "RESULT.json"),
        "stdout": read(ROOT / "control/results" / TASK / "stdout.log"),
        "stderr": read(ROOT / "control/results" / TASK / "stderr.log"),
        "lifecycle": read(ROOT / "control/lifecycle" / f"{TASK}.json"),
    },
    "hourly_timer": {
        "enabled": run(["systemctl", "--user", "is-enabled", TIMER]),
        "active": run(["systemctl", "--user", "is-active", TIMER]),
        "show": unit_show(
            TIMER,
            [
                "ActiveState",
                "SubState",
                "UnitFileState",
                "Result",
                "LastTriggerUSec",
                "NextElapseUSecRealtime",
                "Triggers",
                "FragmentPath",
            ],
        ),
    },
    "hourly_service": {
        "active": run(["systemctl", "--user", "is-active", SERVICE]),
        "failed": run(["systemctl", "--user", "is-failed", SERVICE]),
        "show": unit_show(
            SERVICE,
            [
                "ActiveState",
                "SubState",
                "Result",
                "ExecMainCode",
                "ExecMainStatus",
                "ActiveEnterTimestamp",
                "InactiveExitTimestamp",
                "FragmentPath",
            ],
        ),
    },
    "timer_list": run(
        [
            "systemctl",
            "--user",
            "list-timers",
            "--all",
            "--no-pager",
        ]
    ),
    "hourly_journal": run(
        [
            "journalctl",
            "--user",
            "-u",
            TIMER,
            "-u",
            SERVICE,
            "--since",
            "2026-09-22 15:45:00",
            "--no-pager",
            "-n",
            "300",
        ],
        timeout=20,
    ),
    "linger": run(
        ["loginctl", "show-user", os.environ.get("USER", ""), "-p", "Linger"]
    ),
    "cadence_state": safe_json(
        Path.home() / ".local/state/prediction-research/work_cadence.json"
    ),
    "git": {
        "head": run(["git", "rev-parse", "HEAD"]),
        "branch": run(["git", "branch", "--show-current"]),
        "status": run(["git", "status", "--porcelain=v1"]),
        "fetch": run(["git", "fetch", "origin", "main"], timeout=20),
        "origin_main": run(["git", "rev-parse", "origin/main"]),
        "divergence": run(
            ["git", "rev-list", "--left-right", "--count", "HEAD...origin/main"]
        ),
        "recent_log": run(["git", "log", "-8", "--oneline", "--decorate"]),
    },
    "runtime": {
        "latest_hourly_runs": latest_hourly_runs(),
        "expected_1600_exists": (
            ROOT / "knowledge/runs/hourly-20260922T160000+0200.json"
        ).exists(),
        "registry": safe_json(ROOT / "agents/registry.json"),
        "e007_marker_in_hourly_cycle": "E007_SIX_DOMAIN"
        in read(ROOT / "control/hourly/hourly_cycle.py"),
    },
    "guardrails": {
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "openai_api": False,
    },
}

print(json.dumps(result, indent=2, sort_keys=True))
