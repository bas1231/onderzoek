from urllib.request import Request, urlopen
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

URLS = [
    "https://help.kalshi.com/en/articles/13823837-weather-markets",
    "https://weather.com/kalshi",
    "https://developer.weather.com/docs/openapi/historical-conditions-hourly-3-0",
    "https://developer.weather.com/docs/openapi/time-series-observations-current-hours-past-24-0-0",
]

root = Path.home() / ".local/state/prediction-research/source-lock"
root.mkdir(parents=True, exist_ok=True)

out = {
    "schema": "WX_TWC_SOURCE_LOCK_V1",
    "retrieved_at": datetime.now(timezone.utc).isoformat(),
    "sources": [],
}

for url in URLS:
    rec = {"url": url}
    try:
        response = urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30)
        body = response.read()
        sha = hashlib.sha256(body).hexdigest()
        archive_path = root / f"{sha}.html"
        if not archive_path.exists():
            archive_path.write_bytes(body)
        text = body.decode("utf-8", "ignore").lower()
        rec.update({
            "status": getattr(response, "status", 200),
            "sha256": sha,
            "bytes": len(body),
            "archive": str(archive_path),
            "signals": {
                "the_weather_company": "the weather company" in text,
                "station_coordinates": "station coordinates" in text,
                "weather_com_kalshi": "weather.com/kalshi" in text,
                "preliminary": "preliminary" in text,
                "rounding": "rounding" in text,
                "historical_hourly": "historical conditions hourly" in text,
                "physical_observation_stations": "physical site-based observation stations" in text,
            },
        })
    except Exception as exc:
        rec.update({
            "status": "ERROR",
            "error": f"{type(exc).__name__}: {exc}",
        })
    out["sources"].append(rec)

print(json.dumps(out, indent=2, sort_keys=True))
assert any(
    item.get("status") == 200
    for item in out["sources"]
    if "help.kalshi.com" in item["url"]
), "KALSHI_PRIMARY_SOURCE_CAPTURE_FAILED"
