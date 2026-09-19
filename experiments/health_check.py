import json
import platform
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[1]

payload = {
    "status": "ok",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "python": platform.python_version(),
    "platform": platform.platform(),
}

output = root / "evidence/CONTROL-HEALTH"
output.mkdir(parents=True, exist_ok=True)

(output / "health.json").write_text(
    json.dumps(payload, indent=2) + "\n"
)

print(json.dumps(payload, indent=2))
