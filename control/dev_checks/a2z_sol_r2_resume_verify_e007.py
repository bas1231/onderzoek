from __future__ import annotations
import hashlib
import json
import subprocess
import time
from pathlib import Path

ROOT = Path.home() / ".local/share/prediction-project-executor/campaigns/FULL-A2Z-LIVE-20261004-V4"
TASK_ID = "A2Z-V4-SOL-PROPOSAL-20261006-R2"
UNIT = "prediction-a2z-v4-model@A2Z-V4-SOL-PROPOSAL-20261006-R2.service"
RESULT = ROOT / "model_results" / (TASK_ID + ".json")
REQUEST = ROOT / "requests" / (TASK_ID + ".json")
EXPECTED_ROUTE = "SESSION-ROUTE-756bff225d5a976edf6da02b"
EXPECTED_CANDIDATE = "AUTO-DISCOVERY-54d13314c7879b58e46d"

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

if not RESULT.is_file():
    cp = subprocess.run(
        ["systemctl", "--user", "start", UNIT],
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if cp.returncode != 0:
        detail = (cp.stdout + cp.stderr).replace("\n", " ")[-400:]
        print("SOL_R2_CLASS=SERVICE_START_FAILED RC=" + str(cp.returncode) + " DETAIL=" + detail)
        raise SystemExit(10)

    deadline = time.monotonic() + 180
    while not RESULT.exists() and time.monotonic() < deadline:
        time.sleep(5)

if not RESULT.is_file() or RESULT.is_symlink():
    jp = subprocess.run(
        ["journalctl", "--user", "-u", UNIT, "-n", "80", "--no-pager"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=20,
        check=False,
    )
    lines = [x.strip() for x in (jp.stdout or "").splitlines() if x.strip()]
    interesting = [
        x for x in lines
        if any(k in x.lower() for k in ("usage", "limit", "quota", "error", "failed", "paused", "retry"))
    ]
    last = (interesting[-1] if interesting else (lines[-1] if lines else "NO_JOURNAL"))
    print("SOL_R2_CLASS=NO_RESULT_AFTER_RESUME DETAIL=" + " ".join(last.split())[:500])
    raise SystemExit(11)

result = json.loads(RESULT.read_text(encoding="utf-8"))
for key, wanted in {
    "schema": "PVA_GOVERNED_MODEL_COMPLETION_V1",
    "task_id": TASK_ID,
    "phase": "SOL_PROPOSAL",
    "model": "gpt-5.6-sol",
    "model_policy": "SOL_EXACT",
    "route_task_id": EXPECTED_ROUTE,
    "campaign_id": "FULL-A2Z-LIVE-20261004-V4",
}.items():
    if result.get(key) != wanted:
        print("SOL_R2_CLASS=RESULT_FIELD_MISMATCH FIELD=" + key + " GOT=" + repr(result.get(key)))
        raise SystemExit(12)

if not REQUEST.is_file() or REQUEST.is_symlink():
    print("SOL_R2_CLASS=REQUEST_MISSING")
    raise SystemExit(13)
if result.get("request_sha256") != sha256(REQUEST):
    print("SOL_R2_CLASS=REQUEST_HASH_MISMATCH")
    raise SystemExit(14)

checkpoint = str(result.get("checkpoint") or "")
run_dir = (ROOT / checkpoint).resolve()
if not run_dir.is_relative_to(ROOT.resolve()):
    print("SOL_R2_CLASS=CHECKPOINT_OUTSIDE_CAMPAIGN")
    raise SystemExit(15)

worker = run_dir / "WORKER.json"
complete = run_dir / "COMPLETE.json"
if not worker.is_file() or worker.is_symlink():
    print("SOL_R2_CLASS=WORKER_MISSING")
    raise SystemExit(16)
if not complete.is_file() or complete.is_symlink():
    print("SOL_R2_CLASS=COMPLETE_MISSING")
    raise SystemExit(17)
if result.get("worker_sha256") != sha256(worker):
    print("SOL_R2_CLASS=WORKER_HASH_MISMATCH")
    raise SystemExit(18)
if result.get("completion_sha256") != sha256(complete):
    print("SOL_R2_CLASS=COMPLETION_HASH_MISMATCH")
    raise SystemExit(19)

worker_obj = json.loads(worker.read_text(encoding="utf-8"))
sel = worker_obj.get("model_selection")
if worker_obj.get("model") != "gpt-5.6-sol":
    print("SOL_R2_CLASS=WORKER_WRONG_MODEL")
    raise SystemExit(20)
if not isinstance(sel, dict) or sel.get("policy") != "SOL_EXACT" or sel.get("selected_slug") != "gpt-5.6-sol":
    print("SOL_R2_CLASS=WORKER_SELECTION_INVALID")
    raise SystemExit(21)

final = result.get("final")
if not isinstance(final, str) or not final.strip():
    print("SOL_R2_CLASS=FINAL_MISSING")
    raise SystemExit(22)
try:
    proposal = json.loads(final)
except json.JSONDecodeError as exc:
    print("SOL_R2_CLASS=FINAL_NOT_PURE_JSON DETAIL=" + str(exc))
    raise SystemExit(23)

if not isinstance(proposal, dict):
    print("SOL_R2_CLASS=PROPOSAL_NOT_OBJECT")
    raise SystemExit(24)
if proposal.get("candidate_id") != EXPECTED_CANDIDATE:
    print("SOL_R2_CLASS=CANDIDATE_MISMATCH")
    raise SystemExit(25)
if proposal.get("proposal_version") != 2:
    print("SOL_R2_CLASS=VERSION_MISMATCH")
    raise SystemExit(26)

safety = proposal.get("safety")
if not isinstance(safety, dict):
    print("SOL_R2_CLASS=SAFETY_NOT_OBJECT")
    raise SystemExit(27)
for key in ("live_trading", "paid_actions", "wallet_actions"):
    if safety.get(key) is not False:
        print("SOL_R2_CLASS=SAFETY_NOT_FALSE FIELD=" + key)
        raise SystemExit(28)

scope = proposal.get("data_and_time_scope")
records = scope.get("records") if isinstance(scope, dict) else None
expected = [
    ("v1-stream-001", "0.62", "0.43", "0.00", "0.00"),
    ("v1-stream-002", "0.61", "0.44", "0.00", "0.00"),
    ("v1-stream-003", "0.60", "0.45", "0.00", "0.00"),
]
if not isinstance(records, list) or len(records) != 3:
    print("SOL_R2_CLASS=FROZEN_STREAM_COUNT")
    raise SystemExit(29)
for row, values in zip(records, expected):
    observed = (
        row.get("observation_id"),
        row.get("yes_ask"),
        row.get("no_ask"),
        row.get("yes_fee"),
        row.get("no_fee"),
    ) if isinstance(row, dict) else None
    if observed != values:
        print("SOL_R2_CLASS=FROZEN_STREAM_CHANGED GOT=" + repr(observed))
        raise SystemExit(30)

limitations = proposal.get("scientific_limitations")
if not isinstance(limitations, dict) or limitations.get("required_conclusion") != "NO_PROVEN_EDGE":
    print("SOL_R2_CLASS=SCIENTIFIC_LIMIT_INVALID")
    raise SystemExit(31)

proposal_sha = hashlib.sha256(
    json.dumps(proposal, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
).hexdigest()

print("SOL_R2_RESUMED_AND_VERIFIED=1")
print("SOL_R2_MODEL=gpt-5.6-sol")
print("SOL_R2_POLICY=SOL_EXACT")
print("SOL_R2_PROPOSAL_VERSION=2")
print("SOL_R2_SAFETY_FALSE_TRIPLE=1")
print("SOL_R2_FROZEN_STREAM_UNCHANGED=1")
print("SOL_R2_PROPOSAL_SHA256=" + proposal_sha)
print("NEXT_GATE=ASTRA_PREBUILD")
