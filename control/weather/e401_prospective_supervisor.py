#!/usr/bin/env python3
"""Prospective read-only E401 market-data supervisor.

Discovers currently open hourly temperature events for preregistered KWI cities,
archives each discovery decision immutably, then launches the authenticated
read-only Kalshi WebSocket recorder for a short rolling capture window. No order,
wallet, venue-write, paid API, or trading capability is present here.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / ".venv" / "bin" / "python"
ENV_FILE = Path.home() / ".config" / "prediction-research" / "kalshi_readonly.env"
STATE = Path.home() / ".local" / "state" / "prediction-research"
MANIFESTS = STATE / "e401_prospective_manifests"
BASE = "https://external-api.kalshi.com/trade-api/v2"
SERIES = {
    "nyc": "KXTEMPNYCH",
    "miami": "KXTEMPMIAH",
    "chicago": "KXTEMPCHIH",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_local_env() -> None:
    if not ENV_FILE.is_file():
        raise RuntimeError("kalshi_readonly.env missing")
    for raw in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if sep and key:
            os.environ[key] = value


def get_json(path: str, params: dict[str, object]) -> dict:
    query = urllib.parse.urlencode(params)
    req = urllib.request.Request(
        BASE + path + "?" + query,
        headers={"User-Agent": "PredictionResearch-E401-prospective/1"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def discover_open() -> dict:
    rows = []
    all_tickers = set()
    for city, series in SERIES.items():
        row = {"city": city, "series": series, "events": [], "error": None}
        try:
            payload = get_json("/events", {
                "series_ticker": series,
                "status": "open",
                "limit": 200,
                "with_nested_markets": "true",
            })
            for event in payload.get("events") or []:
                markets = event.get("markets") or []
                tickers = sorted({m.get("ticker") for m in markets if m.get("ticker")})
                if not tickers:
                    continue
                all_tickers.update(tickers)
                row["events"].append({
                    "event_ticker": event.get("event_ticker"),
                    "market_count": len(tickers),
                    "market_tickers": tickers,
                })
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}:{str(exc)[:200]}"
        rows.append(row)
    return {
        "retrieved_at": now_iso(),
        "series": rows,
        "tickers": sorted(all_tickers),
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
        "economic_conclusion": "NO_PROVEN_EDGE",
    }


def write_manifest(prefix: str, payload: dict) -> Path:
    MANIFESTS.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(body).hexdigest()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    path = MANIFESTS / f"{prefix}-{stamp}-{digest[:12]}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def run_capture(tickers: list[str], duration_sec: float) -> dict:
    cmd = [str(PYTHON), "control/weather/kalshi_market_reaction_ws.py"]
    for ticker in tickers:
        cmd.extend(["--ticker", ticker])
    cmd.extend(["--duration-sec", str(duration_sec)])
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=max(30, int(duration_sec) + 30),
        env=os.environ.copy(),
    )
    try:
        summary = json.loads(proc.stdout.strip())
    except Exception:
        summary = {}
    return {
        "returncode": proc.returncode,
        "summary": summary,
        "stderr_tail": proc.stderr[-1000:],
    }


def cycle(capture_sec: float, discovery_only: bool = False) -> dict:
    discovery = discover_open()
    discovery_path = write_manifest("discovery", discovery)
    tickers = discovery["tickers"]
    result = {
        "started_at": discovery["retrieved_at"],
        "discovery_manifest": str(discovery_path),
        "ticker_count": len(tickers),
        "event_count": sum(len(row["events"]) for row in discovery["series"]),
        "cities_with_open_events": sorted(row["city"] for row in discovery["series"] if row["events"]),
        "capture": None,
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
        "economic_conclusion": "NO_PROVEN_EDGE",
    }
    if tickers and not discovery_only:
        result["capture"] = run_capture(tickers, capture_sec)
    result["finished_at"] = now_iso()
    result_path = write_manifest("cycle", result)
    result["cycle_manifest"] = str(result_path)
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture-sec", type=float, default=55.0)
    ap.add_argument("--idle-sec", type=float, default=15.0)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--discovery-only", action="store_true")
    args = ap.parse_args()

    if args.capture_sec <= 0 or args.idle_sec <= 0:
        raise RuntimeError("capture/idle seconds must be positive")
    load_local_env()

    while True:
        try:
            report = cycle(args.capture_sec, args.discovery_only)
            print(json.dumps(report, sort_keys=True), flush=True)
        except Exception as exc:
            report = {
                "status": "cycle_error",
                "retrieved_at": now_iso(),
                "error_type": type(exc).__name__,
                "error": str(exc)[:300],
                "live_trading": False,
                "paid_action": False,
                "wallet_action": False,
                "economic_conclusion": "NO_PROVEN_EDGE",
            }
            write_manifest("error", report)
            print(json.dumps(report, sort_keys=True), flush=True)

        if args.once:
            return 0
        if args.discovery_only or report.get("ticker_count", 0) == 0:
            time.sleep(args.idle_sec)
        else:
            time.sleep(0.25)


if __name__ == "__main__":
    raise SystemExit(main())
