#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

ROOT = Path.home() / "prediction_research_weather"
PYTHON = Path.home() / "prediction_research/.venv/bin/python"
BRANCH = "ai/weather-madis-ldm-a19b"
V1_JOB = ROOT / "control/jobs/weather_away_a19b.py"
V1_REPORT = ROOT / "evidence/weather/WEATHER-AWAY-A19B-latest.json"
V1_PROOF = ROOT / "evidence/weather/A19B_V1_IMMUTABLE_PROOF.json"
V2_JOB = ROOT / "control/jobs/validate_madis_ldm_a19b_v2_strict.py"


def run(*args: str, timeout: int = 1800):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)


def load_obj(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def parse_obj(text: str) -> dict:
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def emit(payload: dict, code: int = 0):
    payload.update({
        "economic_conclusion": "NO_PROVEN_EDGE",
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
    })
    print(json.dumps(payload, indent=2, sort_keys=True))
    raise SystemExit(code)


def git_blob(path: str) -> str | None:
    cp = run("git", "rev-parse", f"HEAD:{path}", timeout=30)
    return cp.stdout.strip() if cp.returncode == 0 and cp.stdout.strip() else None


if not ROOT.is_dir():
    emit({"status": "BLOCKED", "next_gate": "WEATHER_WORKTREE_MISSING"}, 2)
if not PYTHON.is_file():
    emit({"status": "BLOCKED", "next_gate": "PREDICTION_VENV_PYTHON_MISSING"}, 3)

branch = run("git", "branch", "--show-current", timeout=30).stdout.strip()
if branch != BRANCH:
    emit({
        "status": "BLOCKED",
        "next_gate": "WRONG_WEATHER_BRANCH",
        "expected_branch": BRANCH,
        "actual_branch": branch,
    }, 4)

tracked = run("git", "status", "--porcelain", "--untracked-files=no", timeout=30)
if tracked.returncode != 0 or tracked.stdout.strip():
    emit({
        "status": "BLOCKED",
        "next_gate": "WEATHER_WORKTREE_TRACKED_CHANGES",
        "detail": tracked.stdout[-4000:] or tracked.stderr[-4000:],
    }, 5)

pull = run("git", "pull", "--ff-only", "origin", BRANCH, timeout=120)
if pull.returncode != 0:
    emit({
        "status": "BLOCKED",
        "next_gate": "WEATHER_BRANCH_FAST_FORWARD_FAILED",
        "stdout": pull.stdout[-4000:],
        "stderr": pull.stderr[-4000:],
    }, 6)

head = run("git", "rev-parse", "HEAD", timeout=30).stdout.strip()
steps: dict[str, object] = {}

proof = load_obj(V1_PROOF) if V1_PROOF.is_file() else {}
source_blobs = proof.get("source_blobs") if isinstance(proof.get("source_blobs"), dict) else {}
blob_mismatches: dict[str, dict[str, str | None]] = {}
for path, expected in source_blobs.items():
    actual = git_blob(str(path))
    if actual != expected:
        blob_mismatches[str(path)] = {"expected": str(expected), "actual": actual}

proof_valid = bool(
    proof.get("status") == "PASS"
    and proof.get("proof_exit_code") == 0
    and ((proof.get("proof_stdout_claims") or {}).get("a19b_validation_pass") is True)
    and bool(source_blobs)
    and not blob_mismatches
)

latest = load_obj(V1_REPORT) if V1_REPORT.is_file() else {}
latest_valid = bool(
    latest.get("status") == "PASS"
    and (((latest.get("steps") or {}).get("a19b_three_gate_validation") or {}).get("parsed") or {}).get("status") == "PASS"
)

if proof_valid:
    steps["a19b_v1"] = {
        "status": "ALREADY_SATISFIED_IMMUTABLE_PROOF",
        "proof": str(V1_PROOF),
        "proof_task_id": proof.get("proof_task_id"),
        "proof_finished_at": proof.get("proof_finished_at"),
        "source_blob_count": len(source_blobs),
        "source_blobs_match": True,
        "mutable_latest_status": latest.get("status"),
        "next_action": "ADVANCE_TO_A19B_V2_STRICT",
    }
elif not V1_PROOF.is_file() and latest_valid:
    steps["a19b_v1"] = {
        "status": "ALREADY_SATISFIED_LEGACY_LATEST",
        "report": str(V1_REPORT),
        "next_action": "ADVANCE_TO_A19B_V2_STRICT",
    }
else:
    steps["a19b_v1_proof_check"] = {
        "proof_present": V1_PROOF.is_file(),
        "proof_valid": proof_valid,
        "source_blob_mismatches": blob_mismatches,
        "mutable_latest_status": latest.get("status"),
    }
    if not V1_JOB.is_file():
        emit({
            "status": "BLOCKED",
            "weather_head": head,
            "steps": steps,
            "next_gate": "A19B_V1_JOB_MISSING",
        }, 7)
    v1 = run(str(PYTHON), str(V1_JOB.relative_to(ROOT)), timeout=1200)
    steps["a19b_v1"] = {
        "status": "PASS" if v1.returncode == 0 else "FAILED",
        "returncode": v1.returncode,
        "stdout": v1.stdout[-10000:],
        "stderr": v1.stderr[-5000:],
    }
    if v1.returncode != 0:
        emit({
            "status": "BLOCKED_LOCAL_VALIDATION",
            "weather_head": head,
            "steps": steps,
            "next_gate": "FIX_A19B_V1_THREE_GATE_VALIDATION",
        }, 8)

if not V2_JOB.is_file():
    emit({
        "status": "BLOCKED_LOCAL_BUILD",
        "weather_head": head,
        "steps": steps,
        "next_gate": "A19B_V2_STRICT_VALIDATOR_MISSING",
    }, 9)

v2 = run(str(PYTHON), str(V2_JOB.relative_to(ROOT)), timeout=1200)
v2_obj = parse_obj(v2.stdout)
steps["a19b_v2_strict"] = {
    "status": v2_obj.get("status") or ("PASS" if v2.returncode == 0 else "FAILED"),
    "returncode": v2.returncode,
    "next_gate": v2_obj.get("next_gate"),
    "checks": v2_obj.get("checks"),
    "clock_readiness": v2_obj.get("clock_readiness"),
    "ldm_runtime_inventory": v2_obj.get("ldm_runtime_inventory"),
    "queue_insertion_evidence_state": v2_obj.get("queue_insertion_evidence_state"),
    "stderr": v2.stderr[-5000:],
}

if v2.returncode != 0 or v2_obj.get("status") != "PASS_LOCAL_BUILD":
    emit({
        "status": "BLOCKED_LOCAL_VALIDATION",
        "weather_head": head,
        "steps": steps,
        "next_gate": v2_obj.get("next_gate") or "FIX_A19B_V2_STRICT_FAILED_CHECK",
        "terminal_for_current_authorization": False,
    }, 10)

next_gate = str(v2_obj.get("next_gate") or "UNKNOWN_A19B_V2_GATE")
external_or_system_gate = next_gate in {
    "BLOCKED_CLOCK_EVIDENCE",
    "BLOCKED_NOAA_MADIS_LDM_ACCESS_OR_RUNTIME",
}

emit({
    "status": "COMPLETED_LOCAL_RESEARCH_GATE",
    "weather_head": head,
    "steps": steps,
    "next_gate": next_gate,
    "a19b_v1_rerun_policy": "IMMUTABLE_PROOF_REUSED_ONLY_WHILE_BOUND_SOURCE_BLOBS_MATCH",
    "a19b_v2_local_build": "PASS_STRICT",
    "terminal_for_current_authorization": external_or_system_gate,
}, 0)
