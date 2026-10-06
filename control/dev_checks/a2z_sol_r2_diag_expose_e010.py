from __future__ import annotations
import json
import sqlite3
from pathlib import Path

ROOT = Path.home() / ".local/share/prediction-project-executor/campaigns/FULL-A2Z-LIVE-20261004-V4"
RUNTIME = ROOT / "models"
TASK_ID = "A2Z-V4-SOL-PROPOSAL-20261006-R2"
RUNS = RUNTIME / "runs"
RESULT = ROOT / "model_results" / (TASK_ID + ".json")
DB = RUNTIME / "runtime.sqlite"

if RESULT.is_file() and not RESULT.is_symlink():
    print("R2_CLASS=RESULT_PRESENT RESULT_EXISTS=1")
    raise SystemExit(10)

runs = [p for p in RUNS.glob(TASK_ID + "-*") if p.is_dir()] if RUNS.is_dir() else []
latest = max(runs, key=lambda p: p.stat().st_mtime) if runs else None

status = "NO_TASK_ROW"
attempt = 0
reason = "NO_TRANSITION"
retry = 0.0
checkpoint = ""
if DB.is_file() and not DB.is_symlink():
    db = sqlite3.connect("file:" + str(DB) + "?mode=ro", uri=True)
    try:
        row = db.execute("select status,attempt,run from tasks where id=?", (TASK_ID,)).fetchone()
        tr = db.execute(
            "select state,reason,attempt,checkpoint,retry from transitions where task=? order by seq desc limit 1",
            (TASK_ID,),
        ).fetchone()
    finally:
        db.close()
    if row:
        status = str(row[0])
        attempt = int(row[1] or 0)
        checkpoint = str(row[2] or "")
    if tr:
        reason = str(tr[1] or "NO_REASON")
        attempt = int(tr[2] or attempt or 0)
        checkpoint = str(tr[3] or checkpoint)
        retry = float(tr[4] or 0)

if latest is None:
    print(
        "R2_CLASS=NO_RUN_UNDER_MODELS RESULT_EXISTS=0"
        + " TASK_STATUS=" + status
        + " ATTEMPT=" + str(attempt)
        + " REASON=" + reason
        + " CHECKPOINT=" + checkpoint
        + " RETRY_AT=" + str(retry)
    )
    raise SystemExit(10)

events_path = latest / "events.jsonl"
stderr_path = latest / "stderr.log"
worker_path = latest / "WORKER.json"
worker_error_path = latest / "worker_error.json"
complete_path = latest / "COMPLETE.json"

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
event_text = " ".join(json.dumps(e, ensure_ascii=False).lower() for e in events[-30:])
stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace") if stderr_path.is_file() else ""
combined = (event_text + " " + stderr_text.lower())

if any(x in combined for x in ("usage_limit", "usage limit", "quota_exceeded", "you've hit your usage limit", "you’ve hit your usage limit")):
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

worker = {}
if worker_path.is_file():
    try:
        worker = json.loads(worker_path.read_text(encoding="utf-8"))
    except Exception:
        worker = {}

worker_error = ""
if worker_error_path.is_file():
    worker_error = " ".join(worker_error_path.read_text(encoding="utf-8", errors="replace").split())[:260]

stderr_tail = " ".join(stderr_text.split())[-420:] if stderr_text else "NONE"

print(
    "R2_CLASS=" + classification
    + " RESULT_EXISTS=0"
    + " LATEST_RUN=" + latest.name
    + " TASK_STATUS=" + status
    + " ATTEMPT=" + str(attempt)
    + " REASON=" + reason
    + " RETRY_AT=" + str(retry)
    + " EVENT_TYPES=" + ",".join(types[-8:])
    + " MODEL=" + str(worker.get("model"))
    + " POLICY=" + str((worker.get("model_selection") or {}).get("policy"))
    + " COMPLETE=" + ("1" if complete_path.is_file() else "0")
    + " WORKER_ERROR=" + (worker_error or "NONE")
    + " STDERR=" + stderr_tail
)
raise SystemExit(10)
