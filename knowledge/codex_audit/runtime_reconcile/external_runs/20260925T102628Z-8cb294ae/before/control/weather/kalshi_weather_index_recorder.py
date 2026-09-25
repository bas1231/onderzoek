
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlencode
import urllib.request
import json
import hashlib

HOME = Path.home()
STATE = HOME / ".local" / "state" / "prediction-research"
RAW = STATE / "raw" / "kalshi_weather_index"
MANIFESTS = STATE / "kalshi_weather_index_manifests"
BASE = "https://api.elections.kalshi.com/trade-api/v2"
CITIES = ("nyc", "miami", "chicago")

RAW.mkdir(parents=True, exist_ok=True)
MANIFESTS.mkdir(parents=True, exist_ok=True)

def fetch_city(city):
    url = BASE + "/live_data/weather/" + city + "?" + urlencode({"last_sec": 10800, "detailed": "true"})
    req = urllib.request.Request(url, headers={"User-Agent": "PredictionResearch-public-weather-index-recorder"})
    with urllib.request.urlopen(req, timeout=20) as r:
        body = r.read(5_000_000)
        status = int(getattr(r, "status", 200))
        ctype = r.headers.get("Content-Type")
    sha = hashlib.sha256(body).hexdigest()
    city_dir = RAW / city
    city_dir.mkdir(parents=True, exist_ok=True)
    raw_path = city_dir / (sha + ".json")
    if not raw_path.exists():
        raw_path.write_bytes(body)
    data = json.loads(body.decode("utf-8"))
    return {
        "city": city,
        "url": url,
        "status": status,
        "content_type": ctype,
        "sha256": sha,
        "bytes": len(body),
        "data": data,
    }

def classify_points(points):
    latest_any = points[-1] if points else None
    complete = [p for p in points if isinstance(p, dict) and p.get("v") is not None and p.get("status") != "incomplete"]
    latest_complete = complete[-1] if complete else None
    incomplete = [p for p in points if isinstance(p, dict) and p.get("status") == "incomplete"]
    latest_incomplete = incomplete[-1] if incomplete else None
    return latest_any, latest_complete, latest_incomplete

def load_previous(city):
    paths = sorted(MANIFESTS.glob("kwi-*-*.json"))
    for p in reversed(paths):
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for row in obj.get("cities") or []:
            if row.get("city") == city:
                return row
    return None

retrieved_at = datetime.now(timezone.utc).isoformat()
rows = []

for city in CITIES:
    res = fetch_city(city)
    data = res["data"] if isinstance(res["data"], dict) else {}
    points = data.get("timeseries") or []
    latest_any, latest_complete, latest_incomplete = classify_points(points)
    prev = load_previous(city)
    row = {
        "city": city,
        "status": res["status"],
        "content_type": res["content_type"],
        "sha256": res["sha256"],
        "bytes": res["bytes"],
        "config_version": data.get("config_version"),
        "units": data.get("units"),
        "timeseries_count": len(points),
        "latest_any": latest_any,
        "latest_complete": latest_complete,
        "latest_incomplete": latest_incomplete,
        "previous_sha256": prev.get("sha256") if prev else None,
        "payload_changed": (prev.get("sha256") != res["sha256"]) if prev else None,
        "latest_complete_t_changed": (
            (prev.get("latest_complete") or {}).get("t") != (latest_complete or {}).get("t")
        ) if prev else None,
        "latest_complete_v_changed_for_same_t": (
            (prev.get("latest_complete") or {}).get("t") == (latest_complete or {}).get("t")
            and (prev.get("latest_complete") or {}).get("v") != (latest_complete or {}).get("v")
        ) if prev and latest_complete else None,
        "guards": [
            "Public Kalshi weather timeseries availability does not by itself prove contract settlement equivalence.",
            "Incomplete points are not treated as final.",
            "No market edge is inferred without contemporaneous executable market data.",
        ],
    }
    rows.append(row)

manifest = {
    "retrieved_at": retrieved_at,
    "source": "Kalshi public live_data weather endpoint",
    "cities": rows,
    "live_trading": False,
    "paid_actions": False,
    "wallet_actions": False,
}
stamp = retrieved_at.replace(":", "").replace("-", "").replace("+00:00", "Z")
combined = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode("utf-8")).hexdigest()
path = MANIFESTS / ("kwi-" + stamp + "-" + combined[:12] + ".json")
path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({
    "manifest": str(path),
    "retrieved_at": retrieved_at,
    "cities": rows,
    "live_trading": False,
    "paid_actions": False,
    "wallet_actions": False,
}, indent=2))
