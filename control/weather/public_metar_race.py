#!/usr/bin/env python3
"""Prospective public METAR source-race recorder.

Research purpose only. The recorder measures when the same METAR observation is
first visible through multiple *public* sources and through the public TWC/Kalshi
weather feed. It does not place orders and does not infer an economic edge.

Sources:
- NOAA/NWS Aviation Weather Center Data API (batch query)
- NWS tgftp per-station latest METAR files
- weather.com public Kalshi METAR endpoint already used by this repository

Evidence rules:
- collector receipt time is local CLOCK_REALTIME sampled around each HTTP read;
- source-provided timestamps are kept separately and never substituted for local
  receipt time;
- one observation episode is keyed by station + observation timestamp;
- revisions are retained as distinct payload hashes;
- raw HTTP bodies are content-addressed and immutable;
- source lead is only a source-timing result, never market/execution proof.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
import calendar
import gzip
import hashlib
import json
from pathlib import Path
import re
import signal
import sqlite3
import time
from typing import Iterable
from urllib.parse import urlencode
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

HOME = Path.home()
STATE = HOME / ".local" / "state" / "prediction-research"
RAW = STATE / "raw" / "weather_public_race"
DB_PATH = STATE / "weather_public_race.sqlite3"
MANIFESTS = STATE / "weather_public_race_manifests"

AWC_URL = "https://aviationweather.gov/api/data/metar"
TGFTP_BASE = "https://tgftp.nws.noaa.gov/data/observations/metar/stations/"
TWC_URL = "https://weather.com/kalshi/api/metar"
USER_AGENT = "PredictionResearch-public-metar-race/1.0"

DEFAULT_INTERVAL_SEC = 5.0
DEFAULT_MAX_STATIONS = 12
HTTP_TIMEOUT_SEC = 8.0
MAX_BODY = 6_000_000
METAR_TIME_RE = re.compile(r"\b(\d{2})(\d{2})(\d{2})Z\b")
STOP = False


@dataclass(frozen=True)
class Observation:
    source: str
    station: str
    obs_time_ns: int
    raw_text: str
    temperature_c: float | None
    source_time_ns: int | None
    source_status: str | None
    payload_sha256: str
    receipt_start_ns: int
    receipt_end_ns: int
    raw_path: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_from_ns(value: int | None) -> str | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value / 1_000_000_000, tz=timezone.utc).isoformat()


def parse_time_ns(value) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        x = float(value)
        if x <= 0:
            return None
        # AWC obsTime is seconds. Be defensive for ms/us/ns inputs.
        if x >= 1e17:
            return int(x)
        if x >= 1e14:
            return int(x * 1_000)
        if x >= 1e11:
            return int(x * 1_000_000)
        return int(x * 1_000_000_000)
    text = str(value).strip()
    if not text:
        return None
    try:
        return parse_time_ns(float(text))
    except ValueError:
        pass
    try:
        normalized = text.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1_000_000_000)
    except Exception:
        return None


def metar_ddhhmm_to_ns(raw: str, reference: datetime) -> int | None:
    """Map a METAR DDHHMMZ token to the nearest plausible UTC datetime."""
    match = METAR_TIME_RE.search(raw or "")
    if not match:
        return None
    day, hour, minute = map(int, match.groups())
    if not (1 <= day <= 31 and 0 <= hour <= 23 and 0 <= minute <= 59):
        return None

    candidates: list[datetime] = []
    y, m = reference.year, reference.month
    for delta in (-1, 0, 1):
        mm = m + delta
        yy = y
        while mm < 1:
            mm += 12
            yy -= 1
        while mm > 12:
            mm -= 12
            yy += 1
        if day > calendar.monthrange(yy, mm)[1]:
            continue
        candidates.append(datetime(yy, mm, day, hour, minute, tzinfo=timezone.utc))
    if not candidates:
        return None
    best = min(candidates, key=lambda dt: abs((dt - reference).total_seconds()))
    # Reject obviously malformed/stale date mapping. Latest station files can be
    # old during outages, but a month-scale mismatch is not useful race evidence.
    if abs((best - reference).total_seconds()) > 20 * 86400:
        return None
    return int(best.timestamp() * 1_000_000_000)


def content_path(source: str, body: bytes, suffix: str = ".bin") -> tuple[str, str]:
    digest = hashlib.sha256(body).hexdigest()
    directory = RAW / source
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{digest}{suffix}"
    if not path.exists():
        path.write_bytes(body)
    return digest, str(path)


def http_get(url: str, timeout: float = HTTP_TIMEOUT_SEC) -> tuple[bytes, dict, int, int, int]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    start_ns = time.time_ns()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read(MAX_BODY)
        status = int(getattr(response, "status", 200))
        headers = dict(response.headers.items())
    end_ns = time.time_ns()
    return body, headers, status, start_ns, end_ns


def normalize_station(value) -> str | None:
    station = str(value or "").strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{4}", station):
        return None
    return station


def parse_awc(body: bytes, start_ns: int, end_ns: int, raw_path: str, payload_sha: str) -> list[Observation]:
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        return []
    if not isinstance(payload, list):
        return []
    out: list[Observation] = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        station = normalize_station(row.get("icaoId"))
        obs_ns = parse_time_ns(row.get("obsTime"))
        raw = str(row.get("rawOb") or "").strip()
        if station is None or obs_ns is None or not raw:
            continue
        temp = row.get("temp")
        try:
            temp_c = None if temp is None else float(temp)
        except (TypeError, ValueError):
            temp_c = None
        out.append(Observation(
            source="awc_api",
            station=station,
            obs_time_ns=obs_ns,
            raw_text=raw,
            temperature_c=temp_c,
            source_time_ns=parse_time_ns(row.get("receiptTime")),
            source_status=None,
            payload_sha256=payload_sha,
            receipt_start_ns=start_ns,
            receipt_end_ns=end_ns,
            raw_path=raw_path,
        ))
    return out


def parse_twc(body: bytes, start_ns: int, end_ns: int, raw_path: str, payload_sha: str) -> list[Observation]:
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        return []
    if not isinstance(payload, dict):
        return []
    fetched_ns = parse_time_ns(payload.get("fetchedAt"))
    out: list[Observation] = []
    for station_obj in payload.get("stations") or []:
        if not isinstance(station_obj, dict):
            continue
        station_default = normalize_station(
            station_obj.get("icaoId") or station_obj.get("stationId") or station_obj.get("id")
        )
        for row in station_obj.get("observations") or []:
            if not isinstance(row, dict):
                continue
            station = normalize_station(row.get("icaoId")) or station_default
            obs_ns = parse_time_ns(row.get("reportTimeUTC") or row.get("obsTime") or row.get("time"))
            if station is None or obs_ns is None:
                continue
            # TWC rows need not expose literal raw METAR. Canonical row JSON is
            # retained so revisions remain independently hashable/auditable.
            raw = str(row.get("rawOb") or row.get("rawText") or "").strip()
            if not raw:
                raw = json.dumps(row, sort_keys=True, separators=(",", ":"))
            temp = row.get("tempC")
            try:
                temp_c = None if temp is None else float(temp)
            except (TypeError, ValueError):
                temp_c = None
            out.append(Observation(
                source="twc_kalshi",
                station=station,
                obs_time_ns=obs_ns,
                raw_text=raw,
                temperature_c=temp_c,
                source_time_ns=fetched_ns,
                source_status=None if row.get("status") is None else str(row.get("status")),
                payload_sha256=payload_sha,
                receipt_start_ns=start_ns,
                receipt_end_ns=end_ns,
                raw_path=raw_path,
            ))
    return out


def parse_tgftp(station: str, body: bytes, start_ns: int, end_ns: int, raw_path: str, payload_sha: str) -> list[Observation]:
    text = body.decode("utf-8", errors="replace").strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    raw = " ".join(lines[1:]) if len(lines) > 1 else lines[0]
    ref = datetime.fromtimestamp(end_ns / 1_000_000_000, tz=timezone.utc)
    obs_ns = metar_ddhhmm_to_ns(raw, ref)
    if obs_ns is None:
        return []
    header_ns = parse_time_ns(lines[0].replace("/", "-") + ":00+00:00") if len(lines) > 1 else None
    return [Observation(
        source="nws_tgftp",
        station=station,
        obs_time_ns=obs_ns,
        raw_text=raw,
        temperature_c=None,
        source_time_ns=header_ns,
        source_status=None,
        payload_sha256=payload_sha,
        receipt_start_ns=start_ns,
        receipt_end_ns=end_ns,
        raw_path=raw_path,
    )]


def init_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=15)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            station TEXT NOT NULL,
            obs_time_ns INTEGER NOT NULL,
            raw_sha256 TEXT NOT NULL,
            raw_text TEXT NOT NULL,
            temperature_c REAL,
            source_time_ns INTEGER,
            source_status TEXT,
            payload_sha256 TEXT NOT NULL,
            receipt_start_ns INTEGER NOT NULL,
            receipt_end_ns INTEGER NOT NULL,
            raw_path TEXT NOT NULL,
            inserted_at_ns INTEGER NOT NULL,
            UNIQUE(source, station, obs_time_ns, raw_sha256)
        );
        CREATE INDEX IF NOT EXISTS idx_weather_race_episode
            ON observations(station, obs_time_ns, source, receipt_end_ns);
        CREATE TABLE IF NOT EXISTS fetches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            url TEXT NOT NULL,
            started_ns INTEGER NOT NULL,
            finished_ns INTEGER NOT NULL,
            http_status INTEGER,
            payload_sha256 TEXT,
            parsed_count INTEGER NOT NULL,
            error TEXT
        );
        """
    )
    return conn


def store_fetch(conn: sqlite3.Connection, *, source: str, url: str, started_ns: int, finished_ns: int,
                http_status: int | None, payload_sha256: str | None, parsed_count: int, error: str | None) -> None:
    conn.execute(
        "INSERT INTO fetches(source,url,started_ns,finished_ns,http_status,payload_sha256,parsed_count,error) VALUES(?,?,?,?,?,?,?,?)",
        (source, url, started_ns, finished_ns, http_status, payload_sha256, parsed_count, error),
    )


def store_observations(conn: sqlite3.Connection, rows: Iterable[Observation]) -> int:
    inserted = 0
    now_ns = time.time_ns()
    for row in rows:
        raw_sha = hashlib.sha256(row.raw_text.encode("utf-8")).hexdigest()
        cur = conn.execute(
            """INSERT OR IGNORE INTO observations(
                source,station,obs_time_ns,raw_sha256,raw_text,temperature_c,source_time_ns,
                source_status,payload_sha256,receipt_start_ns,receipt_end_ns,raw_path,inserted_at_ns
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                row.source, row.station, row.obs_time_ns, raw_sha, row.raw_text, row.temperature_c,
                row.source_time_ns, row.source_status, row.payload_sha256, row.receipt_start_ns,
                row.receipt_end_ns, row.raw_path, now_ns,
            ),
        )
        inserted += max(0, cur.rowcount)
    return inserted


def known_twc_stations(conn: sqlite3.Connection, limit: int) -> list[str]:
    rows = conn.execute(
        "SELECT station, MAX(receipt_end_ns) AS t FROM observations WHERE source='twc_kalshi' GROUP BY station ORDER BY t DESC, station"
    ).fetchall()
    return sorted({str(row[0]) for row in rows[:limit]})


def fetch_twc(week_start: str) -> tuple[list[Observation], set[str], dict]:
    url = TWC_URL + "?" + urlencode({"primary": "true", "weekStart": week_start})
    start = time.time_ns()
    try:
        body, _headers, status, start, end = http_get(url)
        digest, path = content_path("twc_kalshi", body, ".json")
        rows = parse_twc(body, start, end, path, digest)
        stations = {row.station for row in rows}
        return rows, stations, {
            "source": "twc_kalshi", "url": url, "started_ns": start, "finished_ns": end,
            "http_status": status, "payload_sha256": digest, "parsed_count": len(rows), "error": None,
        }
    except Exception as exc:
        end = time.time_ns()
        return [], set(), {
            "source": "twc_kalshi", "url": url, "started_ns": start, "finished_ns": end,
            "http_status": None, "payload_sha256": None, "parsed_count": 0,
            "error": f"{type(exc).__name__}: {exc}"[:500],
        }


def fetch_awc(stations: list[str]) -> tuple[list[Observation], dict]:
    url = AWC_URL + "?" + urlencode({"ids": ",".join(stations), "format": "json"})
    start = time.time_ns()
    try:
        body, _headers, status, start, end = http_get(url)
        digest, path = content_path("awc_api", body, ".json")
        rows = parse_awc(body, start, end, path, digest)
        return rows, {
            "source": "awc_api", "url": url, "started_ns": start, "finished_ns": end,
            "http_status": status, "payload_sha256": digest, "parsed_count": len(rows), "error": None,
        }
    except Exception as exc:
        end = time.time_ns()
        return [], {
            "source": "awc_api", "url": url, "started_ns": start, "finished_ns": end,
            "http_status": None, "payload_sha256": None, "parsed_count": 0,
            "error": f"{type(exc).__name__}: {exc}"[:500],
        }


def fetch_one_tgftp(station: str) -> tuple[list[Observation], dict]:
    url = TGFTP_BASE + station + ".TXT"
    start = time.time_ns()
    try:
        body, _headers, status, start, end = http_get(url)
        digest, path = content_path("nws_tgftp", body, ".txt")
        rows = parse_tgftp(station, body, start, end, path, digest)
        return rows, {
            "source": "nws_tgftp", "url": url, "started_ns": start, "finished_ns": end,
            "http_status": status, "payload_sha256": digest, "parsed_count": len(rows), "error": None,
        }
    except Exception as exc:
        end = time.time_ns()
        return [], {
            "source": "nws_tgftp", "url": url, "started_ns": start, "finished_ns": end,
            "http_status": None, "payload_sha256": None, "parsed_count": 0,
            "error": f"{type(exc).__name__}: {exc}"[:500],
        }


def fetch_tgftp(stations: list[str]) -> tuple[list[Observation], list[dict]]:
    if not stations:
        return [], []
    rows: list[Observation] = []
    meta: list[dict] = []
    workers = min(8, len(stations))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch_one_tgftp, station): station for station in stations}
        for future in as_completed(futures):
            try:
                obs, item = future.result()
            except Exception as exc:
                station = futures[future]
                now = time.time_ns()
                obs, item = [], {
                    "source": "nws_tgftp", "url": TGFTP_BASE + station + ".TXT",
                    "started_ns": now, "finished_ns": now, "http_status": None,
                    "payload_sha256": None, "parsed_count": 0,
                    "error": f"future:{type(exc).__name__}: {exc}"[:500],
                }
            rows.extend(obs)
            meta.append(item)
    return rows, meta


def current_week_start() -> str:
    ny = utc_now().astimezone(ZoneInfo("America/New_York"))
    return (ny.date() - __import__("datetime").timedelta(days=ny.weekday())).isoformat()


def cycle(conn: sqlite3.Connection, configured_stations: list[str], max_stations: int) -> dict:
    cycle_start = time.time_ns()
    twc_rows, twc_stations, twc_meta = fetch_twc(current_week_start())
    store_fetch(conn, **twc_meta)
    inserted = store_observations(conn, twc_rows)

    if configured_stations:
        stations = configured_stations[:max_stations]
    else:
        stations = sorted(twc_stations)[:max_stations]
        if not stations:
            stations = known_twc_stations(conn, max_stations)

    awc_rows: list[Observation] = []
    awc_meta = None
    if stations:
        awc_rows, awc_meta = fetch_awc(stations)
        store_fetch(conn, **awc_meta)
        inserted += store_observations(conn, awc_rows)

    tg_rows, tg_meta = fetch_tgftp(stations)
    for item in tg_meta:
        store_fetch(conn, **item)
    inserted += store_observations(conn, tg_rows)
    conn.commit()

    cycle_end = time.time_ns()
    errors = [m["error"] for m in [twc_meta, awc_meta, *tg_meta] if m and m.get("error")]
    return {
        "started_at": iso_from_ns(cycle_start),
        "finished_at": iso_from_ns(cycle_end),
        "duration_ms": round((cycle_end - cycle_start) / 1_000_000, 3),
        "stations": stations,
        "station_count": len(stations),
        "parsed": {
            "twc_kalshi": len(twc_rows),
            "awc_api": len(awc_rows),
            "nws_tgftp": len(tg_rows),
        },
        "new_revision_rows": inserted,
        "errors": errors[:30],
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
        "economic_conclusion": "NO_PROVEN_EDGE",
    }


def write_manifest(report: dict) -> Path:
    MANIFESTS.mkdir(parents=True, exist_ok=True)
    body = json.dumps(report, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(body).hexdigest()
    stamp = utc_now().strftime("%Y%m%dT%H%M%S.%fZ")
    path = MANIFESTS / f"public-metar-race-{stamp}-{digest[:12]}.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _stop(_signum, _frame):
    global STOP
    STOP = True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stations", default="", help="optional comma-separated ICAO list; default=discover from TWC feed")
    parser.add_argument("--max-stations", type=int, default=DEFAULT_MAX_STATIONS)
    parser.add_argument("--interval-sec", type=float, default=DEFAULT_INTERVAL_SEC)
    parser.add_argument("--duration-sec", type=float, default=0.0, help="0 means run until stopped")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--db", default=str(DB_PATH))
    args = parser.parse_args()

    if args.max_stations < 1 or args.max_stations > 50:
        raise SystemExit("max-stations must be 1..50")
    if args.interval_sec < 1.0:
        raise SystemExit("interval-sec must be >= 1.0")

    configured = []
    for value in args.stations.split(","):
        station = normalize_station(value)
        if station and station not in configured:
            configured.append(station)

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    conn = init_db(Path(args.db).expanduser())
    started = time.monotonic()
    cycles = 0
    last_report: dict = {}
    try:
        while not STOP:
            loop_start = time.monotonic()
            last_report = cycle(conn, configured, args.max_stations)
            cycles += 1
            if args.once:
                break
            if args.duration_sec > 0 and time.monotonic() - started >= args.duration_sec:
                break
            sleep_for = max(0.0, args.interval_sec - (time.monotonic() - loop_start))
            if sleep_for:
                time.sleep(sleep_for)
    finally:
        conn.close()

    summary = {
        "task": "WEATHER-PUBLIC-METAR-SOURCE-RACE",
        "status": "PASS" if cycles > 0 else "NO_CYCLES",
        "cycles": cycles,
        "db": str(Path(args.db).expanduser()),
        "last_cycle": last_report,
        "source_semantics": {
            "awc_api": "official NOAA/NWS Aviation Weather Center public Data API",
            "nws_tgftp": "official NWS public latest-METAR station files",
            "twc_kalshi": "public weather.com Kalshi METAR feed",
        },
        "interpretation_guard": "A repeatable public-source lead is not a market edge without point-in-time Kalshi reaction and execution evidence.",
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
        "economic_conclusion": "NO_PROVEN_EDGE",
    }
    manifest = write_manifest(summary)
    summary["manifest"] = str(manifest)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if cycles > 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
