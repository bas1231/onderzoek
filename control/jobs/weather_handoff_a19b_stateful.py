#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

WEATHER_ROOT = Path.home() / "prediction_research_weather"
CONTROL_ROOT = Path.home() / "prediction_research"
PYTHON = CONTROL_ROOT / ".venv" / "bin" / "python"
BRANCH = "ai/weather-madis-ldm-a19b"
V2_JOB = WEATHER_ROOT / "control/jobs/validate_madis_ldm_a19b_v2.py"
RESULTS_ROOT = CONTROL_ROOT / "control/results"


def run(*args: str, cwd: Path = WEATHER_ROOT, timeout: int = 1800):
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=timeout)


def parse_obj(text: str) -> dict:
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def emit(payload: dict, code: int = 0) -> None:
    payload.update({
        "economic_conclusion": "NO_PROVEN_EDGE",
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
    })
    print(json.dumps(payload, indent=2, sort_keys=True))
    raise SystemExit(code)


def find_v1_executor_proof() -> dict | None:
    """Return a hash-verified immutable executor proof for A19B-v1 PASS.

    Mutable Weather 'latest' files are deliberately not authoritative here.
    A later failed rerun must not erase an earlier valid prerequisite proof.
    """
    if not RESULTS_ROOT.is_dir():
        return None

    candidates = sorted(
        RESULTS_ROOT.glob("WEATHER-AWAY-A19B-BRIDGE-*/RESULT.json"),
        key=lambda p: p.stat().st_mtime_ns,
        reverse=True,
    )
    for result_path in candidates:
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
            stdout_path = result_path.parent / "stdout.log"
            if not stdout_path.is_file():
                continue
            stdout_bytes = stdout_path.read_bytes()
            if sha256_bytes(stdout_bytes) != result.get("stdout_sha256"):
                continue
            if result.get("status") != "completed" or result.get("exit_code") != 0:
                continue
            if result.get("hypothesis_id") != "KAL-WX-INDEX-001":
                continue
            parsed = parse_obj(stdout_bytes.decode("utf-8"))
            if not (
                parsed.get("a19b_validation_pass") is True
                and parsed.get("status") == "PASS"
                and parsed.get("next_gate") == "NOAA_MADIS_LDM_ACCESS_AND_QUEUE_NATIVE_A19B_V2"
            ):
                continue
            return {
                "task_id": result.get("task_id"),
                "result_path": str(result_path),
                "source_commit": result.get("source_commit"),
                "finished_at": result.get("finished_at"),
                "stdout_sha256": result.get("stdout_sha256"),
                "proof": parsed,
            }
        except Exception:
            continue
    return None


if not WEATHER_ROOT.is_dir():
    emit({"status": "BLOCKED", "next_gate": "WEATHER_WORKTREE_MISSING"}, 2)
if not CONTROL_ROOT.is_dir() or not PYTHON.is_file():
    emit({"status": "BLOCKED", "next_gate": "PREDICTION_RUNTIME_MISSING"}, 3)

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
proof = find_v1_executor_proof()
if proof is None:
    emit({
        "status": "BLOCKED_PREREQUISITE_PROOF",
        "weather_head": head,
        "next_gate": "A19B_V1_IMMUTABLE_PASS_PROOF_MISSING",
        "rerun_policy": "FAIL_CLOSED_DO_NOT_BLINDLY_RERUN_V1",
    }, 7)

steps: dict[str, object] = {
    "a19b_v1": {
        "status": "ALREADY_SATISFIED",
        "proof_source": "HASH_VERIFIED_EXECUTOR_RESULT",
        "proof": proof,
        "next_action": "ADVANCE_TO_A19B_V2",
    }
}

if not V2_JOB.is_file():
    emit({
        "status": "BLOCKED_LOCAL_BUILD",
        "weather_head": head,
        "steps": steps,
        "next_gate": "A19B_V2_VALIDATOR_MISSING",
    }, 8)

v2 = run(str(PYTHON), str(V2_JOB.relative_to(WEATHER_ROOT)), timeout=1200)
v2_obj = parse_obj(v2.stdout)
steps["a19b_v2"] = {
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
        "next_gate": v2_obj.get("next_gate") or "FIX_A19B_V2_FAILED_CHECK",
        "terminal_for_current_authorization": False,
    }, 9)

next_gate = str(v2_obj.get("next_gate") or "UNKNOWN_A19B_V2_GATE")
terminal = next_gate in {
    "BLOCKED_CLOCK_EVIDENCE",
    "BLOCKED_NOAA_MADIS_LDM_ACCESS_OR_RUNTIME",
}

emit({
    "status": "COMPLETED_LOCAL_RESEARCH_GATE",
    "weather_head": head,
    "steps": steps,
    "next_gate": next_gate,
    "a19b_v1_rerun_policy": "DO_NOT_REPEAT_WHILE_HASH_VERIFIED_PASS_PROOF_EXISTS",
    "a19b_v2_local_build": "PASS",
    "terminal_for_current_authorization": terminal,
}, 0)
