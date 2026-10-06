from __future__ import annotations
import json
from pathlib import Path

ROOT = Path.home() / ".local/share/prediction-project-executor/campaigns/FULL-A2Z-LIVE-20261004-V4"
prefix = "A2Z-V4-SOL-PROPOSAL-20261006-R2-"
runs = [p for p in (ROOT / "runs").glob(prefix + "*") if p.is_dir()]
if not runs:
    print("R2_LATEST_RUN=NONE")
    raise SystemExit(10)

run = max(runs, key=lambda p: p.stat().st_mtime)
events_path = run / "events.jsonl"
stderr_path = run / "stderr.log"
worker_path = run / "WORKER.json"
worker_error_path = run / "worker_error.json"
complete_path = run / "COMPLETE.json"

events = []
if events_path.is_file():
    for line in events_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if isinstance(obj, dict):
            events.append(obj)

types = [str(e.get("type")) for e in events]
low = " ".join(json.dumps(e, ensure_ascii=False).lower() for e in events[-20:])
if any(x in low for x in ("usage_limit", "usage limit", "quota_exceeded", "you've hit your usage limit", "you’ve hit your usage limit")):
    classification = "USAGE_LIMIT"
elif complete_path.is_file():
    classification = "COMPLETE_FILE_PRESENT"
elif worker_error_path.is_file():
    classification = "WORKER_ERROR"
elif any(t in {"error", "turn.failed"} for t in types):
    classification = "MODEL_ERROR_EVENT"
elif any(t == "turn.completed" for t in types):
    classification = "TURN_COMPLETED_NO_COMPLETE_FILE"
else:
    classification = "INCOMPLETE_OR_PROCESS_FAILURE"

stderr_tail = ""
if stderr_path.is_file():
    stderr_tail = " ".join(stderr_path.read_text(encoding="utf-8", errors="replace").split())[-500:]

worker = {}
if worker_path.is_file():
    try:
        worker = json.loads(worker_path.read_text(encoding="utf-8"))
    except Exception:
        worker = {}

worker_error = ""
if worker_error_path.is_file():
    worker_error = " ".join(worker_error_path.read_text(encoding="utf-8", errors="replace").split())[:300]

print(
    "R2_LATEST_RUN=" + run.name
    + " CLASS=" + classification
    + " EVENTS=" + str(len(events))
    + " TYPES=" + ",".join(types[-8:])
    + " MODEL=" + str(worker.get("model"))
    + " POLICY=" + str((worker.get("model_selection") or {}).get("policy"))
    + " COMPLETE=" + ("1" if complete_path.is_file() else "0")
    + " WORKER_ERROR=" + (worker_error or "NONE")
    + " STDERR=" + (stderr_tail or "NONE")
)
raise SystemExit(0)
