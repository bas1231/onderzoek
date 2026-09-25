from pathlib import Path
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import hashlib
import json
import urllib.request

HOME = Path.home()
RAW_DIR = HOME / ".local/state/prediction-research/raw/twc_hourly_snapshots"
MANIFEST_DIR = HOME / ".local/state/prediction-research/twc_hourly_manifests"
RAW_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST_DIR.mkdir(parents=True, exist_ok=True)

now_utc = datetime.now(timezone.utc)
ny_now = now_utc.astimezone(ZoneInfo("America/New_York"))
week_start = (ny_now.date() - timedelta(days=ny_now.weekday())).isoformat()

url = "https://weather.com/kalshi/api/metar?primary=true&weekStart=" + week_start
request = urllib.request.Request(
    url,
    headers={"User-Agent": "PredictionResearch-public"},
)
with urllib.request.urlopen(request, timeout=30) as response:
    body = response.read(4_000_000)
    http_status = int(getattr(response, "status", 200))
    content_type = response.headers.get("Content-Type")

received_at = datetime.now(timezone.utc)
sha256 = hashlib.sha256(body).hexdigest()
raw_path = RAW_DIR / (sha256 + ".bin")
if not raw_path.exists():
    raw_path.write_bytes(body)

data = json.loads(body.decode("utf-8"))

def flatten(payload):
    rows = {}
    for station in payload.get("stations", []):
        for row in station.get("observations") or []:
            key = (row.get("icaoId"), row.get("reportTimeUTC"))
            rows[key] = row
    return rows

current_rows = flatten(data)

previous_manifest = None
previous_rows = None
manifests = sorted(MANIFEST_DIR.glob("*.json"))
if manifests:
    try:
        previous_manifest = json.loads(manifests[-1].read_text(encoding="utf-8"))
        if previous_manifest.get("weekStart") == week_start:
            previous_sha = previous_manifest.get("sha256")
            previous_raw = RAW_DIR / (str(previous_sha) + ".bin")
            if previous_raw.exists():
                previous_rows = flatten(json.loads(previous_raw.read_text(encoding="utf-8")))
    except Exception:
        previous_manifest = None
        previous_rows = None

status_counts = {}
for row in current_rows.values():
    status = row.get("status")
    status_counts[status] = status_counts.get(status, 0) + 1

summary = {
    "timestamp_semantics": "response_body_received",
    "request_started_at": now_utc.isoformat(),
    "retrieved_at": received_at.isoformat(),
    "weekStart": week_start,
    "http_status": http_status,
    "content_type": content_type,
    "bytes": len(body),
    "sha256": sha256,
    "fetchedAt": data.get("fetchedAt"),
    "station_count": len(data.get("stations", [])),
    "observation_count": len(current_rows),
    "status_counts": status_counts,
    "previous_manifest": None if previous_manifest is None else previous_manifest.get("manifest_name"),
    "common_count": None,
    "added_count": None,
    "removed_count": None,
    "status_change_count": None,
    "temperature_change_count": None,
    "pending_to_settled_count": None,
    "pending_to_settled_temperature_change_count": None,
    "settled_to_settled_temperature_change_count": None,
    "changes_sample": [],
    "paid_actions": False,
    "live_trading": False,
    "wallet_actions": False,
    "interpretation_guard": "TWC feed status is not assumed to equal Kalshi contract settlement finality."
}

if previous_rows is not None:
    old_keys = set(previous_rows)
    new_keys = set(current_rows)
    common = old_keys & new_keys
    status_changes = []
    temperature_changes = []
    change_rows = []
    for key in sorted(common):
        old = previous_rows[key]
        new = current_rows[key]
        status_changed = old.get("status") != new.get("status")
        temperature_changed = (
            old.get("tempC") != new.get("tempC")
            or old.get("tempF") != new.get("tempF")
        )
        if status_changed:
            status_changes.append((old, new))
        if temperature_changed:
            temperature_changes.append((old, new))
        if status_changed or temperature_changed:
            if len(change_rows) < 100:
                change_rows.append({
                    "icaoId": key[0],
                    "reportTimeUTC": key[1],
                    "old_status": old.get("status"),
                    "new_status": new.get("status"),
                    "old_tempC": old.get("tempC"),
                    "new_tempC": new.get("tempC"),
                    "old_tempF": old.get("tempF"),
                    "new_tempF": new.get("tempF"),
                })
    summary["common_count"] = len(common)
    summary["added_count"] = len(new_keys - old_keys)
    summary["removed_count"] = len(old_keys - new_keys)
    summary["status_change_count"] = len(status_changes)
    summary["temperature_change_count"] = len(temperature_changes)
    summary["pending_to_settled_count"] = sum(
        1 for old, new in status_changes
        if old.get("status") == "pending" and new.get("status") == "settled"
    )
    summary["pending_to_settled_temperature_change_count"] = sum(
        1 for old, new in temperature_changes
        if old.get("status") == "pending" and new.get("status") == "settled"
    )
    summary["settled_to_settled_temperature_change_count"] = sum(
        1 for old, new in temperature_changes
        if old.get("status") == "settled" and new.get("status") == "settled"
    )
    summary["changes_sample"] = change_rows

stamp = received_at.strftime("%Y%m%dT%H%M%SZ")
manifest_name = "twc-hourly-" + stamp + "-" + sha256[:12] + ".json"
summary["manifest_name"] = manifest_name
manifest_path = MANIFEST_DIR / manifest_name
manifest_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(summary, indent=2, sort_keys=True))
