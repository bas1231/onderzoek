from __future__ import annotations
import json
from pathlib import Path

ROOT = Path.home() / ".local/share/prediction-project-executor/campaigns/FULL-A2Z-LIVE-20261004-V4"
RUN = ROOT / "models" / "runs" / "A2Z-V4-SOL-PROPOSAL-20261006-R2-6-49b9a49f"
events_path = RUN / "events.jsonl"
stderr_path = RUN / "stderr.log"

events = []
if events_path.is_file() and not events_path.is_symlink():
    for line in events_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if isinstance(obj, dict):
            events.append(obj)

interesting = [e for e in events if e.get("type") in {"error", "turn.failed"}]
payload = interesting[-4:] if interesting else events[-4:]
compact = " | ".join(json.dumps(e, ensure_ascii=False, sort_keys=True) for e in payload)
compact = " ".join(compact.split())[:2200]

stderr = "NONE"
if stderr_path.is_file() and not stderr_path.is_symlink():
    stderr = " ".join(stderr_path.read_text(encoding="utf-8", errors="replace").split())[-1200:] or "NONE"

print("SOL_R2_USAGE_SOURCE_DIAG=1 EVENT_PAYLOAD=" + compact + " STDERR=" + stderr)
raise SystemExit(10)
