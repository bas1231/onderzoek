from __future__ import annotations

from pathlib import Path
import hashlib
import json

CANONICAL = Path.cwd()
PROD = Path.home() / "prediction_research_prod"
SYNC_STATUS = Path.home() / ".local/state/prediction-research/prod-runtime-sync-latest.json"

FILES = (
    "control/codex_supervisor/supervisor.py",
    "control/codex_supervisor/candidate_dispatch.py",
    "control/codex_supervisor/build_wake.py",
    "control/tampermonkey_multichat/continuation_manager.py",
    "knowledge/codex_runtime/CONFIG.json",
)

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> int:
    mismatches = []
    observed = {}
    for rel in FILES:
        c = CANONICAL / rel
        p = PROD / rel
        if not c.is_file() or not p.is_file():
            mismatches.append({"path": rel, "reason": "MISSING", "canonical": c.is_file(), "production": p.is_file()})
            continue
        csha = sha(c)
        psha = sha(p)
        observed[rel] = {"canonical_sha256": csha, "production_sha256": psha, "match": csha == psha}
        if csha != psha:
            mismatches.append({"path": rel, "reason": "HASH_MISMATCH", "canonical_sha256": csha, "production_sha256": psha})

    sync = {}
    if SYNC_STATUS.is_file():
        try:
            sync = json.loads(SYNC_STATUS.read_text(encoding="utf-8"))
        except Exception as exc:
            mismatches.append({"path": str(SYNC_STATUS), "reason": "SYNC_STATUS_INVALID", "error": type(exc).__name__})
    else:
        mismatches.append({"path": str(SYNC_STATUS), "reason": "SYNC_STATUS_MISSING"})

    if sync and sync.get("status") != "READY":
        mismatches.append({"path": str(SYNC_STATUS), "reason": "SYNC_NOT_READY", "status": sync.get("status"), "error": sync.get("error")})

    print("PROD_AUTOBUILD_SYNC=" + ("PASS" if not mismatches else "FAIL"), flush=True)
    print("FILES=" + json.dumps(observed, sort_keys=True), flush=True)
    print("SYNC=" + json.dumps({
        "status": sync.get("status"),
        "timestamp_utc": sync.get("timestamp_utc"),
        "head": sync.get("head"),
        "fast_forward": sync.get("fast_forward"),
        "remote_change_count": sync.get("remote_change_count"),
    }, sort_keys=True), flush=True)
    if mismatches:
        print("MISMATCHES=" + json.dumps(mismatches, sort_keys=True), flush=True)
        return 3
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
