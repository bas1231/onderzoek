#!/usr/bin/env python3
"""Enable/disable bounded server-side nightshift heartbeat for one routed chat."""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

HOME = Path.home()
DATA = HOME / ".local" / "share" / "prediction-chat-bridge"
ROUTES = DATA / "routes"
MODE = DATA / "nightshift_mode.json"


def atomic_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    os.replace(tmp, path)


def read_mode() -> dict:
    if not MODE.exists():
        return {}
    try:
        obj = json.loads(MODE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def route_chat(task_id: str) -> str:
    path = ROUTES / f"{task_id}.json"
    if not path.is_file():
        raise RuntimeError("route_missing")
    obj = json.loads(path.read_text(encoding="utf-8"))
    chat_id = str(obj.get("chat_id") or "").strip()
    if not chat_id:
        raise RuntimeError("route_chat_missing")
    return chat_id


def enable(task_id: str, hours: float, interval: float, delay: float) -> None:
    if not (0.25 <= hours <= 12.0):
        raise RuntimeError("hours_out_of_range")
    if not (15.0 <= interval <= 300.0):
        raise RuntimeError("interval_out_of_range")
    if not (0.0 <= delay <= 300.0):
        raise RuntimeError("delay_out_of_range")
    now = time.time()
    chat_id = route_chat(task_id)
    obj = {
        "enabled": True,
        "chat_id": chat_id,
        "started_at": now,
        "not_before": now + delay,
        "expires_at": now + hours * 3600.0,
        "interval_seconds": interval,
        "last_emit_at": 0.0,
        "enabled_by_task": task_id,
    }
    atomic_json(MODE, obj)
    print("NIGHTSHIFT_SERVER_HEARTBEAT=ENABLED")
    print(f"INTERVAL_SECONDS={int(interval)}")
    print(f"DELAY_SECONDS={int(delay)}")
    print(f"EXPIRES_IN_SECONDS={int(hours * 3600)}")


def disable() -> None:
    current = read_mode()
    obj = {
        "enabled": False,
        "disabled_at": time.time(),
    }
    if current.get("enabled_by_task"):
        obj["previous_enabled_by_task"] = current.get("enabled_by_task")
    atomic_json(MODE, obj)
    print("NIGHTSHIFT_SERVER_HEARTBEAT=DISABLED")


def status() -> None:
    obj = read_mode()
    now = time.time()
    enabled = obj.get("enabled") is True and float(obj.get("expires_at") or 0) > now
    print(f"NIGHTSHIFT_SERVER_HEARTBEAT={'ENABLED' if enabled else 'DISABLED'}")
    if enabled:
        print(f"INTERVAL_SECONDS={int(float(obj.get('interval_seconds') or 0))}")
        print(f"SECONDS_REMAINING={max(0, int(float(obj.get('expires_at') or 0) - now))}")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)

    p_enable = sub.add_parser("enable")
    p_enable.add_argument("task_id")
    p_enable.add_argument("--hours", type=float, default=10.0)
    p_enable.add_argument("--interval", type=float, default=25.0)
    p_enable.add_argument("--delay", type=float, default=30.0)

    sub.add_parser("disable")
    sub.add_parser("status")
    args = parser.parse_args()

    if args.action == "enable":
        enable(args.task_id, args.hours, args.interval, args.delay)
    elif args.action == "disable":
        disable()
    else:
        status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
