from __future__ import annotations
import argparse, json, os, pathlib, shutil

PROJECT = pathlib.Path(__file__).resolve().parents[2]
HOURLY = PROJECT / "control" / "hourly"
SUP = PROJECT / "control" / "codex_supervisor"
import sys
sys.path.insert(0, str(HOURLY))
sys.path.insert(0, str(SUP))

import ai_response
import astra_review_wake
import build_wake
import candidate_dispatch
import candidate_queue
import candidate_reporting
import measurement_wake
import model_quality_gate
import supervisor

CID = "AUTO-DISCOVERY-54d13314c7879b58e46d"
FIXTURE = "knowledge/evidence/qualification/FULL-A2Z-LIVE-20261004-V4.json"
RUNTIME = pathlib.Path("/tmp/prediction-full-a2z-live-v4-runtime")
SELECT = pathlib.Path("/tmp/prediction-full-a2z-live-v4-selection")
REPORT = pathlib.Path("/tmp/prediction-full-a2z-live-v4-report.md")
STATE = pathlib.Path("/tmp/prediction-full-a2z-live-v4-state.json")


def load(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(stage: str, **extra):
    old = load(STATE) if STATE.exists() else {"schema":"PVA_FULL_A2Z_LIVE_STATE_V1","candidate_id":CID,"stages":[]}
    old["stages"].append({"stage":stage, **extra})
    STATE.write_text(json.dumps(old, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def candidate_path(repo=PROJECT):
    return pathlib.Path(repo) / "knowledge" / "candidates" / f"{CID}.json"


def verify_scout_fixture():
    fixture = load(PROJECT / FIXTURE)
    proposal = fixture["scout_proposal"]
    ai_response.validate_candidate_proposal(proposal, fixture["scout_role_evidence_refs"])
    expected = ai_response.build_primary_scout_candidate(
        proposal,
        fixture["run_id"],
        fixture["created_at"],
    )
    actual = load(candidate_path())
    for key, value in expected.items():
        if key in {"priority", "evidence_refs"}:
            continue
        if actual.get(key) != value:
            raise RuntimeError(f"SCOUT_CANDIDATE_MISMATCH:{key}")
    if actual.get("priority") != "P0" or actual.get("qualification_priority_override") != "P0_CONTROL_PLANE_ONLY":
        raise RuntimeError("QUALIFICATION_PRIORITY_OVERRIDE_MISSING")
    if actual.get("evidence_refs") != [FIXTURE]:
        raise RuntimeError("QUALIFICATION_EVIDENCE_NOT_BOUND")
    if actual.get("qualification_fixture") is not True:
        raise RuntimeError("QUALIFICATION_MARKER_MISSING")


def rebuild_selection():
    if SELECT.exists():
        shutil.rmtree(SELECT)
    (SELECT / "knowledge" / "candidates").mkdir(parents=True)
    src = candidate_path()
    dst = SELECT / "knowledge" / "candidates" / src.name
    shutil.copy2(src, dst)
    c = load(src)
    refs = []
    if c.get("manual_seed_ref"):
        refs.append(c["manual_seed_ref"])
    for key in ("evidence_refs", "prospective_protocols"):
        refs.extend(c.get(key, []) or [])
    for ref in sorted(set(refs)):
        rel = pathlib.Path(ref)
        source = PROJECT / rel
        if not source.is_file():
            raise RuntimeError("SELECTION_EVIDENCE_MISSING:" + ref)
        target = SELECT / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def queue_assert():
    old = (candidate_queue.ROOT, candidate_queue.CANDIDATES, candidate_queue.RUNS)
    try:
        candidate_queue.ROOT = SELECT
        candidate_queue.CANDIDATES = SELECT / "knowledge" / "candidates"
        candidate_queue.RUNS = SELECT / "knowledge" / "runs"
        q = candidate_queue.build_queue(write_candidates=False)
    finally:
        candidate_queue.ROOT, candidate_queue.CANDIDATES, candidate_queue.RUNS = old
    row = next((x for x in q["queue"] if x.get("candidate_id") == CID), None)
    if not row or row.get("queue_status") not in {"NEEDS_DIRECTOR","RESULT_READY"}:
        raise RuntimeError("TARGET_NOT_IN_CANDIDATE_QUEUE")
    return row


def latest_overlay_path():
    root = RUNTIME / "candidate_states"
    matches = []
    if root.exists():
        for p in root.glob("*.json"):
            obj = load(p)
            if obj.get("candidate_id") == CID:
                try: stamp = float(obj.get("decision_timestamp"))
                except Exception: stamp = -1.0
                matches.append((stamp, p.name, p))
    if not matches:
        raise RuntimeError("TARGET_OVERLAY_MISSING")
    matches.sort()
    return matches[-1][2]


def latest_overlay():
    return load(latest_overlay_path())


def target_source(current):
    task = candidate_dispatch.select_task(current, SELECT)
    if task is None or task.get("candidate_id") != CID:
        raise RuntimeError("TARGET_DIRECTOR_TASK_NOT_SELECTED")
    return task


def director_stage(expected_status: str, stage_name: str):
    rebuild_selection()
    row = queue_assert()
    os.environ["PREDICTION_CODEX_WORKER_TIMEOUT_SECONDS"] = "360"
    s = supervisor.Supervisor(RUNTIME, worker=supervisor.CodexWorker(), candidate_source=target_source)
    result = s.tick("NORMAL")
    if result.get("state") == "PAUSED_USAGE_LIMIT":
        save_state(stage_name, status="PAUSED_USAGE_LIMIT", supervisor=result)
        return 75
    overlay = latest_overlay()
    if overlay.get("queue_status") != expected_status:
        raise RuntimeError(f"{stage_name}_UNEXPECTED_STATUS:{overlay.get('queue_status')}:{overlay.get('finding')}")
    if overlay.get("scientific_status") != "NO_PROVEN_EDGE":
        raise RuntimeError(stage_name + "_SCIENTIFIC_STATUS_UNSAFE")
    save_state(stage_name, status="PASS", queue=row, supervisor=result, overlay_status=overlay.get("queue_status"), finding=overlay.get("finding"), next_action=overlay.get("next_action"))
    return 0


def wake_astra(phase: str):
    p = latest_overlay_path()
    item = load(p)
    required = "ASTRA_PREBUILD_REVIEW" if phase == "PREBUILD" else "ASTRA_PREMEASUREMENT_REVIEW"
    if item.get("queue_status") != required:
        raise RuntimeError("ASTRA_WAKE_WRONG_STATE:" + str(item.get("queue_status")))
    s = supervisor.Supervisor(RUNTIME)
    wake = astra_review_wake.ensure_review_continuation(s, PROJECT, item, phase)
    if wake.get("continuation_state") not in {"CONTINUE_REQUESTED","CONTINUE_QUEUED","CONTINUE_SENT","REVIEW_ALREADY_AVAILABLE"}:
        raise RuntimeError("ASTRA_WAKE_NOT_CREATED:" + str(wake.get("continuation_state")))
    save_state("astra_" + phase.lower() + "_wake", status="PASS", wake=wake)
    return 0


def apply_prebuild_and_wake_build():
    p = latest_overlay_path()
    s = supervisor.Supervisor(RUNTIME)
    updated, ref = model_quality_gate.apply_review(s, PROJECT, p, "PREBUILD")
    if updated is None:
        raise RuntimeError("ASTRA_PREBUILD_REVIEW_NOT_AVAILABLE")
    review = updated.get("astra_reviews", {}).get("PREBUILD", {})
    if review.get("decision") != "APPROVE" or review.get("reviewer_model") != "GPT-6 Astra":
        raise RuntimeError("ASTRA_PREBUILD_NOT_APPROVED:" + str(review.get("decision")))
    if updated.get("queue_status") != "NEEDS_BUILD":
        raise RuntimeError("PREBUILD_DID_NOT_UNLOCK_BUILD")
    wake = build_wake.ensure_build_continuation(s, updated, repo=PROJECT)
    if wake.get("continuation_state") not in {"CONTINUE_REQUESTED","CONTINUE_QUEUED","CONTINUE_SENT","DONE"}:
        raise RuntimeError("BUILD_WAKE_NOT_CREATED:" + str(wake.get("continuation_state")))
    save_state("prebuild_approved_build_wake", status="PASS", review_ref=ref, wake=wake)
    return 0


def apply_premeasurement_and_wake_measurement():
    p = latest_overlay_path()
    s = supervisor.Supervisor(RUNTIME)
    updated, ref = model_quality_gate.apply_review(s, PROJECT, p, "PREMEASUREMENT")
    if updated is None:
        raise RuntimeError("ASTRA_PREMEASUREMENT_REVIEW_NOT_AVAILABLE")
    review = updated.get("astra_reviews", {}).get("PREMEASUREMENT", {})
    if review.get("decision") != "APPROVE" or review.get("reviewer_model") != "GPT-6 Astra":
        raise RuntimeError("ASTRA_PREMEASUREMENT_NOT_APPROVED:" + str(review.get("decision")))
    if updated.get("queue_status") != "MEASUREMENT_READY":
        raise RuntimeError("PREMEASUREMENT_DID_NOT_UNLOCK_MEASUREMENT")
    auth = updated.get("measurement_authorization") or {}
    if auth.get("scope") != "READ_ONLY_PROSPECTIVE_MARKET_DATA" or auth.get("order_submission") is not False:
        raise RuntimeError("MEASUREMENT_AUTHORIZATION_UNSAFE")
    wake = measurement_wake.ensure_measurement_continuation(s, updated, repo=PROJECT)
    if wake.get("continuation_state") not in {"CONTINUE_REQUESTED","CONTINUE_QUEUED","CONTINUE_SENT","DONE"}:
        raise RuntimeError("MEASUREMENT_WAKE_NOT_CREATED:" + str(wake.get("continuation_state")))
    save_state("premeasurement_approved_measurement_wake", status="PASS", review_ref=ref, wake=wake)
    return 0


def final_report():
    rebuild_selection()
    old = (candidate_queue.ROOT, candidate_queue.CANDIDATES, candidate_queue.RUNS)
    try:
        candidate_queue.ROOT = SELECT
        candidate_queue.CANDIDATES = SELECT / "knowledge" / "candidates"
        candidate_queue.RUNS = SELECT / "knowledge" / "runs"
        q = candidate_queue.build_queue(write_candidates=False)
    finally:
        candidate_queue.ROOT, candidate_queue.CANDIDATES, candidate_queue.RUNS = old
    REPORT.write_text("# Full live A-to-Z qualification V4\n\n", encoding="utf-8")
    summary = candidate_reporting.append_to_report(REPORT, q, RUNTIME)
    body = REPORT.read_text(encoding="utf-8")
    overlay = latest_overlay()
    required = [CID, "NO_PROVEN_EDGE", "Astra pre-build: APPROVE", "Astra pre-measurement: APPROVE", "Measurement scope: READ_ONLY_PROSPECTIVE_MARKET_DATA", "Order submission: False"]
    missing = [x for x in required if x not in body]
    if missing:
        raise RuntimeError("FINAL_REPORT_MISSING:" + ",".join(missing))
    if overlay.get("scientific_status") != "NO_PROVEN_EDGE":
        raise RuntimeError("FINAL_SCIENTIFIC_STATUS_UNSAFE")
    save_state("report", status="PASS", final_runtime_status=overlay.get("queue_status"), report_candidate_count=summary.get("candidate_count"), report_path=str(REPORT))
    return 0


def status():
    out = {"candidate": load(candidate_path()), "state": load(STATE) if STATE.exists() else None, "overlay": latest_overlay() if (RUNTIME/"candidate_states").exists() else None}
    print(json.dumps(out, ensure_ascii=False, sort_keys=True))
    return 0


def main():
    p=argparse.ArgumentParser()
    p.add_argument("stage", choices=["director1","wake_prebuild","apply_prebuild_build","director2","wake_premeasurement","apply_premeasurement_measure","director3","report","status"])
    a=p.parse_args()
    if a.stage=="director1":
        verify_scout_fixture()
        return director_stage("ASTRA_PREBUILD_REVIEW","director1")
    if a.stage=="wake_prebuild": return wake_astra("PREBUILD")
    if a.stage=="apply_prebuild_build": return apply_prebuild_and_wake_build()
    if a.stage=="director2": return director_stage("ASTRA_PREMEASUREMENT_REVIEW","director2")
    if a.stage=="wake_premeasurement": return wake_astra("PREMEASUREMENT")
    if a.stage=="apply_premeasurement_measure": return apply_premeasurement_and_wake_measurement()
    if a.stage=="director3":
        rc=director_stage("REJECT","director3")
        return rc
    if a.stage=="report": return final_report()
    return status()

if __name__=="__main__":
    raise SystemExit(main())
