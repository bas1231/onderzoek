#!/usr/bin/env python3
"""A19A: free NOAA MADIS OMO public-file feasibility collector/decoder.

Purpose:
- prove we can archive and decode public 1-minute ASOS (OMO) files;
- inspect station/time/temperature fields without assuming undocumented schema;
- measure public-file freshness only as a batching diagnostic.

This is NOT the LDM latency test. NOAA states public current/previous-hour OMO
files are processed in cycles, while LDM is the recommended fastest real-time
access path. No trading, paid action, credentials, or MADIS application is used.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
import urllib.request

STATE = Path.home() / ".local" / "state" / "prediction-research"
RAW = STATE / "raw" / "madis_omo_public"
MANIFESTS = STATE / "madis_omo_manifests"
INDEX_URL = "https://madis-data.ncep.noaa.gov/madisPublic1/data/LDAD/hfmetar/netCDF/"
FILE_RE = re.compile(r"^(\d{8}_\d{4})\.gz$")
DEFAULT_STATIONS = ("KMIA", "KOPF", "KFLL", "KFXE", "KPMP")  # provisional Miami research set


class _IndexParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.hrefs.append(str(value))


def parse_index(html: str) -> list[str]:
    parser = _IndexParser()
    parser.feed(html)
    names = sorted({Path(h).name for h in parser.hrefs if FILE_RE.match(Path(h).name)})
    return names


def file_valid_hour_ms(name: str) -> int:
    m = FILE_RE.match(name)
    if not m:
        raise ValueError("invalid MADIS OMO filename")
    dt = datetime.strptime(m.group(1), "%Y%m%d_%H%M").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def temp_to_f(value, units: str | None):
    if value is None:
        return None
    x = float(value)
    u = (units or "").strip().lower()
    if u in {"k", "kelvin", "degrees_k", "degree_k"} or "kelvin" in u:
        return (x - 273.15) * 9.0 / 5.0 + 32.0
    if u in {"c", "degc", "celsius", "degrees_c", "degree_c"} or "celsius" in u:
        return x * 9.0 / 5.0 + 32.0
    if u in {"f", "degf", "fahrenheit", "degrees_f", "degree_f"} or "fahrenheit" in u:
        return x
    return None


def _candidate_var(ds, names):
    lower = {str(k).lower(): k for k in ds.variables.keys()}
    for name in names:
        key = lower.get(name.lower())
        if key is not None:
            return ds.variables[key]
    return None


def _strings(var):
    import numpy as np
    arr = var[:]
    try:
        from netCDF4 import chartostring
        if getattr(arr, "ndim", 0) >= 2 and getattr(arr.dtype, "kind", "") in {"S", "U"}:
            arr = chartostring(arr)
    except Exception:
        pass
    flat = np.asarray(arr)
    if flat.ndim == 0:
        flat = flat.reshape(1)
    result = []
    for item in flat:
        if isinstance(item, bytes):
            text = item.decode("utf-8", errors="replace")
        elif hasattr(item, "tobytes") and getattr(item, "ndim", 0) > 0:
            text = item.tobytes().decode("utf-8", errors="replace")
        else:
            text = str(item)
        result.append(text.replace("\x00", "").strip())
    return result


def decode_netcdf(path: Path, stations: set[str]) -> dict:
    try:
        from netCDF4 import Dataset
    except Exception as exc:
        return {
            "status": "BLOCKED_OPTIONAL_DEPENDENCY_NETCDF4",
            "detail": f"{type(exc).__name__}: {exc}",
            "install_hint": "Use the project venv and install the free netCDF4 package before rerunning A19A.",
        }

    with Dataset(path, "r") as ds:
        inventory = {
            name: {
                "dimensions": list(getattr(var, "dimensions", ())),
                "shape": list(getattr(var, "shape", ())),
                "dtype": str(getattr(var, "dtype", "")),
                "units": getattr(var, "units", None),
            }
            for name, var in ds.variables.items()
        }
        station_var = _candidate_var(ds, ["stationName", "stationId", "stationID", "station", "stid"])
        time_var = _candidate_var(ds, ["observationTime", "timeObs", "obsTime", "time"])
        temp_var = _candidate_var(ds, ["temperature", "airTemperature", "temp", "T"])
        if station_var is None or temp_var is None:
            return {
                "status": "SCHEMA_DISCOVERY_REQUIRED",
                "found_station_var": station_var.name if station_var is not None else None,
                "found_temperature_var": temp_var.name if temp_var is not None else None,
                "variable_inventory": inventory,
            }

        station_values = _strings(station_var)
        temps = temp_var[:]
        times = time_var[:] if time_var is not None else None
        units = getattr(temp_var, "units", None)
        rows = []
        for idx, station in enumerate(station_values):
            normalized = station.upper().strip()
            if stations and normalized not in stations:
                continue
            try:
                raw_temp = temps[idx]
                if hasattr(raw_temp, "mask") and bool(raw_temp.mask):
                    continue
                raw_temp = float(raw_temp)
            except Exception:
                continue
            row = {
                "station": normalized,
                "temperature_raw": raw_temp,
                "temperature_units": units,
                "temperature_f": temp_to_f(raw_temp, units),
            }
            if times is not None:
                try:
                    row["observation_time_raw"] = float(times[idx])
                    row["observation_time_units"] = getattr(time_var, "units", None)
                except Exception:
                    pass
            rows.append(row)
        return {
            "status": "PASS",
            "station_variable": station_var.name,
            "temperature_variable": temp_var.name,
            "time_variable": time_var.name if time_var is not None else None,
            "temperature_units": units,
            "matched_rows": rows,
            "matched_station_count": len({r["station"] for r in rows}),
            "requested_stations": sorted(stations),
            "variable_inventory": inventory,
        }


def fetch(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers={"User-Agent": "PredictionResearch-MADIS-OMO-A19A"})
    start_ns = time.time_ns()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read(10_000_000)
        headers = dict(resp.headers.items())
        status = int(getattr(resp, "status", 200))
    end_ns = time.time_ns()
    return status, headers, body, start_ns, end_ns


def run(stations: set[str], download: bool = True) -> dict:
    RAW.mkdir(parents=True, exist_ok=True)
    MANIFESTS.mkdir(parents=True, exist_ok=True)
    retrieved_at = datetime.now(timezone.utc)
    status, headers, html_bytes, idx_start_ns, idx_end_ns = fetch(INDEX_URL)
    html = html_bytes.decode("utf-8", errors="replace")
    names = parse_index(html)
    index_sha = hashlib.sha256(html_bytes).hexdigest()
    index_path = RAW / f"index-{index_sha}.html"
    if not index_path.exists():
        index_path.write_bytes(html_bytes)

    result = {
        "task": "WEATHER-MADIS-OMO-PUBLIC-FEASIBILITY-A19A",
        "status": "PASS" if names else "NO_FILES_DISCOVERED",
        "retrieved_at": retrieved_at.isoformat(),
        "index_url": INDEX_URL,
        "index_http_status": status,
        "index_sha256": index_sha,
        "index_receipt_start_ns": idx_start_ns,
        "index_receipt_end_ns": idx_end_ns,
        "files_discovered": len(names),
        "latest_file": names[-1] if names else None,
        "requested_stations": sorted(stations),
        "station_set_guard": "Requested station list is provisional research input; do not assume it equals the current Kalshi/TWC index configuration.",
        "latency_guard": "Public hourly files are a schema/history feasibility path, not the LDM real-time latency benchmark.",
        "economic_conclusion": "NO_PROVEN_EDGE",
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
    }
    if not names:
        return result

    latest = names[-1]
    valid_ms = file_valid_hour_ms(latest)
    result["latest_file_valid_hour_ms"] = valid_ms
    result["latest_file_age_minutes_at_retrieval"] = round((retrieved_at.timestamp() * 1000 - valid_ms) / 60_000, 3)
    if not download:
        return result

    file_url = INDEX_URL + latest
    f_status, f_headers, gz_bytes, file_start_ns, file_end_ns = fetch(file_url, timeout=60)
    gz_sha = hashlib.sha256(gz_bytes).hexdigest()
    gz_path = RAW / f"{latest[:-3]}-{gz_sha}.gz"
    if not gz_path.exists():
        gz_path.write_bytes(gz_bytes)
    nc_bytes = gzip.decompress(gz_bytes)
    nc_sha = hashlib.sha256(nc_bytes).hexdigest()
    nc_path = RAW / f"{latest[:-3]}-{nc_sha}.nc"
    if not nc_path.exists():
        nc_path.write_bytes(nc_bytes)
    decoded = decode_netcdf(nc_path, stations)
    result.update({
        "file_url": file_url,
        "file_http_status": f_status,
        "file_http_last_modified": f_headers.get("Last-Modified"),
        "file_http_date": f_headers.get("Date"),
        "file_receipt_start_ns": file_start_ns,
        "file_receipt_end_ns": file_end_ns,
        "compressed_bytes": len(gz_bytes),
        "compressed_sha256": gz_sha,
        "netcdf_bytes": len(nc_bytes),
        "netcdf_sha256": nc_sha,
        "decode": decoded,
    })
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stations", default=",".join(DEFAULT_STATIONS), help="comma-separated ICAO IDs")
    ap.add_argument("--index-only", action="store_true")
    args = ap.parse_args()
    stations = {x.strip().upper() for x in args.stations.split(",") if x.strip()}
    result = run(stations, download=not args.index_only)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    path = MANIFESTS / f"madis-omo-a19a-{stamp}.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result["manifest"] = str(path)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") in {"PASS", "NO_FILES_DISCOVERED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
