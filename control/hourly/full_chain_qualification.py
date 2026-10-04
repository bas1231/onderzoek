from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

PROJECT = Path(__file__).resolve().parents[2]
HOURLY = PROJECT / "control/hourly"
SUPERVISOR_DIR = PROJECT / "control/codex_supervisor"
sys.path.insert(0, str(HOURLY))
sys.path.insert(0, str(SUPERVISOR_DIR))

import ai_response
import build_wake
import candidate_dispatch
import candidate_reporting
import candidate_queue
import supervisor

RUN_ID = "hourly-A2ZFULL-20261004T220000+0200"
RESULT_DEFAULT = Path("/tmp/prediction-full-a2z-result.json")
CID_KEY = "qualification-complement-arbitrage-v1"


def save_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("MODULE_LOAD_FAILED:" + name)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ScriptedWorker:
    def __init__(self):
        self.calls = 0

    def __call__(self, task, thread, folder, lock_fd):
        self.calls += 1
        if self.calls == 1:
            payload = {
                "candidate_id": task["candidate_id"],
                "queue_status": "NEEDS_BUILD",
                "finding": "The scout hypothesis is falsifiable but requires the bounded complement-price checker before any economic conclusion.",
                "next_action": "Build the local complement checker, run the frozen no-edge fixture and a positive control, then return immutable build-result evidence.",
                "scientific_status": "NO_PROVEN_EDGE",
            }
        else:
            payload = {
                "candidate_id": task["candidate_id"],
                "queue_status": "REJECT",
                "finding": "The built checker passed its technical tests and the frozen qualification fixture costs 1.05 for a 1.00 payout, so this fixture has no executable complement edge.",
                "next_action": "Record NO_PROVEN_EDGE for the qualification fixture; retain the checker only as tested research tooling.",
                "scientific_status": "NO_PROVEN_EDGE",
            }
        events = [
            {"type": "thread.started", "thread_id": f"qual-thread-{self.calls}"},
            {"type": "item.completed", "item": {"type": "agent_message", "text": json.dumps(payload, sort_keys=True)}},
            {"type": "turn.completed"},
        ]
        (folder / "events.jsonl").write_text("\n".join(json.dumps(x) for x in events) + "\n", encoding="utf-8")
        (folder / "stderr.log").write_text("", encoding="utf-8")
        return 0


def scout_input(repo: Path) -> str:
    original = {
        "ROOT": ai_response.ROOT,
        "RUNS": ai_response.RUNS,
        "PACKETS": ai_response.PACKETS,
        "CANDIDATES": ai_response.CANDIDATES,
    }
    try:
        ai_response.ROOT = repo
        ai_response.RUNS = repo / "knowledge/runs"
        ai_response.PACKETS = ai_response.RUNS / "agent_packets"
        ai_response.CANDIDATES = repo / "knowledge/candidates"
        packet_dir = ai_response.PACKETS / RUN_ID
        packet_dir.mkdir(parents=True, exist_ok=True)
        save_json(packet_dir / "discovery.json", {
            "run_id": RUN_ID,
            "agent_id": "discovery",
            "status": "READY",
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "openai_api": False,
        })
        evidence_refs = ["scout://qualification-fixture", "scout://positive-control"]
        response = {
            "schema": "PVA_AI_RESPONSE_V1",
            "run_id": RUN_ID,
            "economic_conclusion": "NO_PROVEN_EDGE",
            "role_results": [{
                "agent_id": "discovery",
                "status": "COMPLETED",
                "finding": "Qualification scout proposes a bounded complement-price falsification.",
                "evidence_refs": evidence_refs,
                "candidate_ids": [],
                "candidate_proposals": [{
                    "candidate_key": CID_KEY,
                    "lane": "primary_scout",
                    "hypothesis": "A complement-price opportunity exists only when executable YES ask + NO ask + fees is below the 1.00 payout; the frozen qualification fixture is YES=0.62 and NO=0.43.",
                    "mechanism": "Buying complementary outcomes can only create gross arbitrage when total executable acquisition cost is below guaranteed payout.",
                    "open_question": "Can a bounded local checker distinguish the frozen no-edge fixture from a deliberately profitable positive control without hindsight?",
                    "next_decisive_test": "Build a deterministic complement checker; test 0.62+0.43 as NO_EDGE and 0.45+0.45 as EDGE; then submit immutable build-result evidence for Director review.",
                    "evidence_summary": "Synthetic qualification evidence freezes a no-edge fixture and a positive control solely to test the research pipeline.",
                    "evidence_refs": evidence_refs,
                }],
                "capability_results": {},
                "validation_results": [],
                "failure_pattern_ids": [],
                "next_decisive_question": "Does the built checker correctly falsify the frozen fixture?",
                "local_task_required": False,
                "local_task_spec": None,
            }],
            "candidate_decisions": [],
            "director_decision": "Create an unproven qualification candidate for bounded build/falsification.",
            "local_tasks": [],
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "openai_api": False,
        }
        receipt = ai_response.apply_response(response, RUN_ID, write=True)
        if len(receipt.get("candidate_creations", [])) != 1:
            raise RuntimeError("SCOUT_CANDIDATE_CREATION_FAILED")
        files = list(ai_response.CANDIDATES.glob("AUTO-DISCOVERY-*.json"))
        if len(files) != 1:
            raise RuntimeError("SCOUT_CANDIDATE_COUNT_INVALID")
        return json.loads(files[0].read_text())["candidate_id"]
    finally:
        ai_response.ROOT = original["ROOT"]
        ai_response.RUNS = original["RUNS"]
        ai_response.PACKETS = original["PACKETS"]
        ai_response.CANDIDATES = original["CANDIDATES"]


def queue_snapshot(repo: Path):
    original = (candidate_queue.ROOT, candidate_queue.CANDIDATES, candidate_queue.RUNS)
    try:
        candidate_queue.ROOT = repo
        candidate_queue.CANDIDATES = repo / "knowledge/candidates"
        candidate_queue.RUNS = repo / "knowledge/runs"
        return candidate_queue.build_queue(write_candidates=False)
    finally:
        candidate_queue.ROOT, candidate_queue.CANDIDATES, candidate_queue.RUNS = original


def latest_overlay(runtime: Path, cid: str):
    item = candidate_reporting.latest_overlay(runtime, cid)
    if not item:
        raise RuntimeError("OVERLAY_MISSING")
    return item


def invoke_build_wake(s, overlay, work: Path):
    bridge = work / "bridge"
    routes = bridge / "routes"
    routes.mkdir(parents=True, exist_ok=True)
    route_id = "QUAL-ROUTE-A2Z"
    save_json(bridge / "autobuild_control_route.json", {
        "schema": "PREDICTION_AUTOBUILD_ROUTE_V1",
        "route_task_id": route_id,
    })
    save_json(routes / f"{route_id}.json", {
        "schema": "PREDICTION_SESSION_ROUTE_V1",
        "task_id": route_id,
        "chat_id": "QUALCHAT-A2Z-20261004",
    })
    wake = build_wake.ensure_build_continuation(
        s,
        overlay,
        bridge_data=bridge,
        route_config=bridge / "autobuild_control_route.json",
        routes_dir=routes,
    )
    if wake.get("continuation_state") != "CONTINUE_REQUESTED":
        raise RuntimeError("BUILD_CONTINUATION_NOT_CREATED")
    return wake


def build_and_test(repo: Path, cid: str):
    module_path = repo / "control/qualification/a2z_complement_checker.py"
    test_path = repo / "tests/qualification/test_a2z_complement_checker.py"
    module_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.parent.mkdir(parents=True, exist_ok=True)
    module_path.write_text(
        "def evaluate(yes_ask, no_ask, fees=0.0):\n"
        "    total=float(yes_ask)+float(no_ask)+float(fees)\n"
        "    return {'total_cost':round(total,10),'gross_edge':round(1.0-total,10),'has_edge':total < 1.0}\n",
        encoding="utf-8",
    )
    test_path.write_text(
        "import importlib.util\nfrom pathlib import Path\n"
        "P=Path(__file__).resolve().parents[2]/'control/qualification/a2z_complement_checker.py'\n"
        "s=importlib.util.spec_from_file_location('a2z_checker',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\n"
        "def test_frozen_no_edge_fixture():\n"
        "    r=m.evaluate(0.62,0.43);assert r['total_cost']==1.05;assert r['gross_edge']==-0.05;assert r['has_edge'] is False\n"
        "def test_positive_control_detects_edge():\n"
        "    r=m.evaluate(0.45,0.45);assert r['total_cost']==0.9;assert r['gross_edge']==0.1;assert r['has_edge'] is True\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(test_path)],
        cwd=repo,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError("BUILD_TEST_FAILED:" + (proc.stdout + proc.stderr)[-1000:])

    module = load_module(module_path, "qualification_checker")
    frozen = module.evaluate(0.62, 0.43)
    positive = module.evaluate(0.45, 0.45)
    if frozen.get("has_edge") is not False or positive.get("has_edge") is not True:
        raise RuntimeError("SEMANTIC_TEST_FAILED")
    evidence_rel = f"knowledge/experiment_results/{cid}-qualification-build-result.json"
    evidence_path = repo / evidence_rel
    save_json(evidence_path, {
        "schema": "PVA_QUALIFICATION_BUILD_RESULT_V1",
        "candidate_id": cid,
        "build_status": "PASS",
        "artifact_ref": str(module_path.relative_to(repo)),
        "artifact_sha256": sha(module_path),
        "test_ref": str(test_path.relative_to(repo)),
        "test_sha256": sha(test_path),
        "pytest_exit_code": proc.returncode,
        "tests_passed": 2,
        "frozen_fixture": {"yes_ask": 0.62, "no_ask": 0.43, **frozen},
        "positive_control": {"yes_ask": 0.45, "no_ask": 0.45, **positive},
        "economic_conclusion": "NO_PROVEN_EDGE",
        "scientific_status": "NO_PROVEN_EDGE",
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
    })
    candidate_path = next((repo / "knowledge/candidates").glob("AUTO-DISCOVERY-*.json"))
    candidate = json.loads(candidate_path.read_text())
    candidate["queue_status"] = "RESULT_READY"
    candidate["phase"] = "DEVELOPMENT"
    candidate["updated_at"] = "2026-10-04T20:45:00+00:00"
    candidate["evidence_refs"] = [evidence_rel]
    candidate["next_decisive_test"] = "Director review of immutable build/test evidence; decide whether the frozen fixture demonstrates any edge."
    candidate["build_result_ref"] = evidence_rel
    save_json(candidate_path, candidate)
    return evidence_rel, frozen, positive


def run(mode: str, result_path: Path) -> int:
    result = {
        "schema": "PVA_FULL_A2Z_QUALIFICATION_V1",
        "mode": mode,
        "stages": {},
        "economic_conclusion": "NO_PROVEN_EDGE",
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
    }
    try:
        with tempfile.TemporaryDirectory(prefix="prediction-full-a2z-") as td:
            work = Path(td)
            repo = work / "repo"
            runtime = work / "runtime"
            (repo / "knowledge/candidates").mkdir(parents=True)
            cid = scout_input(repo)
            result["candidate_id"] = cid
            result["stages"]["scout_input"] = "PASS"

            q = queue_snapshot(repo)
            row = next((x for x in q["queue"] if x.get("candidate_id") == cid), None)
            if not row or row.get("queue_status") != "NEEDS_DIRECTOR":
                raise RuntimeError("QUEUE_INGRESS_FAILED")
            result["stages"]["candidate_queue"] = "PASS"

            worker = ScriptedWorker() if mode == "deterministic" else supervisor.CodexWorker()
            os.environ["PREDICTION_CODEX_WORKER_TIMEOUT_SECONDS"] = "360" if mode == "live" else "600"
            s = supervisor.Supervisor(
                runtime,
                worker=worker,
                candidate_source=lambda current: candidate_dispatch.select_next(current, repo),
            )
            state1 = s.tick()
            result["first_supervisor_state"] = state1
            if state1.get("state") == "PAUSED_USAGE_LIMIT":
                result["stages"]["director_reasoning_1"] = "PAUSED_USAGE_LIMIT"
                save_json(result_path, result)
                return 75
            overlay1 = latest_overlay(runtime, cid)
            if overlay1.get("queue_status") != "NEEDS_BUILD":
                raise RuntimeError("DIRECTOR_DID_NOT_REQUEST_BUILD:" + str(overlay1.get("queue_status")))
            applied1 = list((runtime / "runs").glob("*/CANDIDATE_APPLIED.json"))
            if not applied1:
                raise RuntimeError("FIRST_CANDIDATE_APPLIED_MISSING")
            result["stages"]["director_reasoning_1"] = "PASS"
            result["stages"]["candidate_applied_1"] = "PASS"

            wake = invoke_build_wake(s, overlay1, work)
            result["build_continuation_id"] = wake.get("continuation_id")
            result["stages"]["build_wake"] = "PASS"

            evidence_ref, frozen, positive = build_and_test(repo, cid)
            result["build_evidence_ref"] = evidence_ref
            result["frozen_fixture"] = frozen
            result["positive_control"] = positive
            result["stages"]["build"] = "PASS"
            result["stages"]["tests"] = "PASS"

            state2 = s.tick()
            result["second_supervisor_state"] = state2
            if state2.get("state") == "PAUSED_USAGE_LIMIT":
                result["stages"]["director_reasoning_2"] = "PAUSED_USAGE_LIMIT"
                save_json(result_path, result)
                return 75
            overlay2 = latest_overlay(runtime, cid)
            if overlay2.get("scientific_status") != "NO_PROVEN_EDGE":
                raise RuntimeError("UNSAFE_FINAL_SCIENTIFIC_STATUS")
            if overlay2.get("queue_status") == "NEEDS_BUILD":
                raise RuntimeError("FINAL_REVIEW_LOOPED_TO_BUILD")
            applied = list((runtime / "runs").glob("*/CANDIDATE_APPLIED.json"))
            if len(applied) < 2:
                raise RuntimeError("SECOND_CANDIDATE_APPLIED_MISSING")
            result["final_runtime_status"] = overlay2.get("queue_status")
            result["final_finding"] = overlay2.get("finding")
            result["final_next_action"] = overlay2.get("next_action")
            result["stages"]["director_reasoning_2"] = "PASS"
            result["stages"]["candidate_applied_2"] = "PASS"

            q2 = queue_snapshot(repo)
            report_path = repo / "hourly-reports/hourly-A2ZFULL-qualification.md"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(
                "# Full A-to-Z qualification\n\n"
                "Scout input: synthetic complement-price hypothesis.\n"
                "Build: bounded deterministic checker.\n"
                "Tests: frozen no-edge fixture plus positive control.\n\n",
                encoding="utf-8",
            )
            summary = candidate_reporting.append_to_report(report_path, q2, runtime)
            report = report_path.read_text(encoding="utf-8")
            if cid not in report or "NO_PROVEN_EDGE" not in report or str(overlay2.get("queue_status")) not in report:
                raise RuntimeError("FINAL_REPORT_MISSING_DECISION")
            result["report_sha256"] = sha(report_path)
            result["report_candidate_count"] = summary.get("candidate_count")
            result["stages"]["reporting"] = "PASS"
            result["stages"]["edge_decision"] = "PASS"
            result["economic_conclusion"] = "NO_PROVEN_EDGE"
            result["status"] = "PASS"
            save_json(result_path, result)
            return 0
    except Exception as exc:
        result["status"] = "FAIL"
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)[:1000]
        save_json(result_path, result)
        return 1


def assert_result(path: Path, stage: str) -> int:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if stage == "overall":
        return 0 if obj.get("status") == "PASS" else 1
    if stage == "no_edge":
        return 0 if obj.get("economic_conclusion") == "NO_PROVEN_EDGE" and obj.get("status") == "PASS" else 1
    return 0 if obj.get("stages", {}).get(stage) == "PASS" else 1


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["deterministic", "live"], default="deterministic")
    p.add_argument("--result", type=Path, default=RESULT_DEFAULT)
    p.add_argument("--assert-stage")
    a = p.parse_args()
    if a.assert_stage:
        return assert_result(a.result, a.assert_stage)
    return run(a.mode, a.result)


if __name__ == "__main__":
    raise SystemExit(main())
