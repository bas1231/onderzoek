from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = Path.home() / ".local/state/prediction-research/watchdog"
STATUS_FILE = STATE_DIR / "status.json"
EVENTS_FILE = STATE_DIR / "events.jsonl"
REPAIRS_FILE = STATE_DIR / "repairs.json"
BRIDGE_STATE = Path.home() / ".config/prediction-research/bridge_state.json"

SERVICES = [
    "prediction-research-executor.service",
    "prediction-research-browser-bridge.service",
]
CHECK_INTERVAL = 15
PENDING_STALE_SECONDS = 90
RESULT_STALE_SECONDS = 90
HEARTBEAT_STALE_SECONDS = 90
MAX_REPAIRS_PER_KEY = 3
REPAIR_COOLDOWN_SECONDS = 60


def now() -> float:
    return time.time()


def iso(ts: float | None = None) -> str:
    return datetime.fromtimestamp(ts or now(), timezone.utc).isoformat()


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + chr(10),
        encoding="utf-8",
    )
    tmp.replace(path)


def emit(kind: str, detail: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    row = {"timestamp": iso(), "kind": kind, "detail": detail}
    with EVENTS_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + chr(10))


def run(args: list[str], timeout: int = 20):
    return subprocess.run(
        args,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def service_active(name: str) -> bool:
    return (
        run(["systemctl", "--user", "is-active", name]).stdout.strip()
        == "active"
    )


def restart_service(name: str) -> bool:
    proc = run(["systemctl", "--user", "restart", name])
    return proc.returncode == 0 and service_active(name)


def queue_status() -> str:
    path = ROOT / "control/TASK_QUEUE.yaml"
    if not path.exists():
        return "MISSING"
    for line in path.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines():
        if line.strip().startswith("queue_status:"):
            return line.split(":", 1)[1].strip()
    return "UNKNOWN"


def age(path: Path, ts: float) -> int:
    return max(0, int(ts - path.stat().st_mtime))


def committed(relative_path: str) -> bool:
    proc = run(["git", "cat-file", "-e", "HEAD:" + relative_path])
    return proc.returncode == 0


def repair_allowed(key: str, repairs: dict, ts: float) -> bool:
    item = repairs.get(key, {})
    count = int(item.get("count", 0))
    last = float(item.get("last", 0))
    return (
        count < MAX_REPAIRS_PER_KEY
        and ts - last >= REPAIR_COOLDOWN_SECONDS
    )


def note_repair(key: str, repairs: dict, ts: float) -> None:
    item = repairs.get(key, {})
    repairs[key] = {
        "count": int(item.get("count", 0)) + 1,
        "last": ts,
    }


def browser_heartbeat_recent() -> bool:
    proc = run(
        [
            "journalctl",
            "--user",
            "-u",
            "prediction-research-browser-bridge.service",
            "--since",
            f"{HEARTBEAT_STALE_SECONDS} seconds ago",
            "--no-pager",
        ]
    )
    return "GET /health HTTP/1.1" in proc.stdout


def inspect(allow_repairs: bool = True) -> dict:
    ts = now()
    repairs = load_json(REPAIRS_FILE, {})
    qstatus = queue_status()
    issues: list[dict] = []
    services = {name: service_active(name) for name in SERVICES}

    for name, active in services.items():
        if active:
            continue
        issue = {"code": "SERVICE_DOWN", "service": name}
        key = "service:" + name
        if allow_repairs and repair_allowed(key, repairs, ts):
            ok = restart_service(name)
            note_repair(key, repairs, ts)
            issue["auto_repair_attempted"] = True
            issue["auto_repair_success"] = ok
            emit("AUTO_REPAIR", {"key": key, "success": ok})
        issues.append(issue)

    pending = ROOT / "control/tasks/pending"
    if pending.exists():
        for path in sorted(pending.glob("*.json")):
            task = load_json(path, {})
            task_id = str(task.get("task_id") or path.stem)
            task_class = str(task.get("task_class") or "")

            if task_class == "research" and qstatus != "ACTIVE":
                continue

            task_age = age(path, ts)
            if task_age <= PENDING_STALE_SECONDS:
                continue

            rel = str(path.relative_to(ROOT))
            is_committed = committed(rel)
            issue = {
                "code": (
                    "PENDING_STALE"
                    if is_committed
                    else "PENDING_NOT_COMMITTED"
                ),
                "task_id": task_id,
                "task_class": task_class,
                "age_seconds": task_age,
                "committed": is_committed,
            }

            if is_committed and task_class == "infrastructure":
                key = "pending:" + task_id
                if allow_repairs and repair_allowed(key, repairs, ts):
                    ok = restart_service(
                        "prediction-research-executor.service"
                    )
                    note_repair(key, repairs, ts)
                    issue["auto_repair_attempted"] = True
                    issue["auto_repair_success"] = ok
                    emit("AUTO_REPAIR", {"key": key, "success": ok})

            issues.append(issue)

    bridge_state = load_json(
        BRIDGE_STATE,
        {"bridge_tasks": [], "acked": []},
    )
    acked = set(bridge_state.get("acked", []))

    for task_id in bridge_state.get("bridge_tasks", []):
        if task_id in acked:
            continue
        result_file = (
            ROOT / "control/results" / task_id / "RESULT.json"
        )
        if (
            result_file.exists()
            and age(result_file, ts) > RESULT_STALE_SECONDS
        ):
            issues.append(
                {
                    "code": "RESULT_DELIVERY_STALE",
                    "task_id": task_id,
                    "age_seconds": age(result_file, ts),
                    "auto_repair_attempted": False,
                }
            )

    heartbeat = browser_heartbeat_recent()
    if not heartbeat:
        issues.append(
            {
                "code": "BROWSER_HEARTBEAT_STALE",
                "auto_repair_attempted": False,
                "note": (
                    "WSL cannot force Chrome content-script reinjection; "
                    "preserve state and wait for browser reconnect"
                ),
            }
        )

    atomic_json(REPAIRS_FILE, repairs)

    snapshot = {
        "timestamp": iso(ts),
        "status": "HEALTHY" if not issues else "DEGRADED",
        "queue_status": qstatus,
        "services": {
            name: service_active(name)
            for name in SERVICES
        },
        "browser_heartbeat_recent": heartbeat,
        "issues": issues,
        "guardrails": {
            "research_auto_resume_allowed": False,
            "paid_actions_allowed": False,
            "live_trading_allowed": False,
            "wallet_actions_allowed": False,
            "running_task_kill_allowed": False,
            "max_repairs_per_key": MAX_REPAIRS_PER_KEY,
        },
    }

    atomic_json(STATUS_FILE, snapshot)
    return snapshot


def loop() -> None:
    previous = None
    while True:
        try:
            snapshot = inspect(allow_repairs=True)
            fingerprint = json.dumps(
                snapshot.get("issues", []),
                sort_keys=True,
            )
            if fingerprint != previous:
                emit(
                    "STATE_CHANGE",
                    {
                        "status": snapshot["status"],
                        "issues": snapshot["issues"],
                    },
                )
            previous = fingerprint
        except Exception as exc:
            emit("WATCHDOG_EXCEPTION", {"error": repr(exc)})
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.loop:
        loop()
    else:
        print(
            json.dumps(
                inspect(allow_repairs=not args.once),
                indent=2,
                sort_keys=True,
            )
        )
