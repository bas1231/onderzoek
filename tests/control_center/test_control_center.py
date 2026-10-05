from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "control/control_center/server.py"
spec = importlib.util.spec_from_file_location("prediction_control_center_server", SERVER)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")


@pytest.fixture()
def model(tmp_path):
    repo = tmp_path / "repo"
    state = tmp_path / "state"
    (repo / "knowledge/candidates").mkdir(parents=True)
    (repo / "knowledge/runs/agent_packets").mkdir(parents=True)
    (repo / "knowledge/manual_scout_seeds").mkdir(parents=True)
    (repo / "knowledge/research").mkdir(parents=True)

    write_json(
        repo / "knowledge/candidates/C-1.json",
        {
            "candidate_id": "C-1",
            "created_at": "2026-10-01T10:00:00Z",
            "updated_at": "2026-10-01T12:00:00Z",
            "hypothesis": "Late market pricing may lag settlement reality.",
            "lane": "microstructure",
            "phase": "SHADOW",
            "queue_status": "RUNNING",
            "decision": "UNPROVEN",
            "scientific_status": "NO_PROVEN_EDGE",
            "gates": {"mechanism": "PASS", "shadow": "PENDING"},
            "evidence_refs": ["knowledge/runs/R-1.json"],
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
        },
    )
    write_json(
        repo / "knowledge/runs/R-1.json",
        {
            "run_id": "R-1",
            "started_at": "2026-10-01T11:00:00Z",
            "status": "COMPLETED",
            "decision": "NO_PROVEN_EDGE",
            "candidate_id": "C-1",
            "agents": {"scout": "COMPLETED", "research_director": "COMPLETED"},
        },
    )
    packet = repo / "knowledge/runs/agent_packets/R-1/scout.json"
    write_json(packet, {"run_id": "R-1", "agent_id": "scout", "finding": "candidate"})
    (repo / "knowledge/manual_scout_seeds/old-idea.md").write_text(
        "# Old idea\nA historical idea that predates canonical candidate records.",
        encoding="utf-8",
    )
    (repo / "knowledge/research/legacy-note.md").write_text("# Legacy research", encoding="utf-8")

    m = mod.ControlCenterModel(repo, state)
    m.command_state = tmp_path / "command_state"
    m.executor_state = tmp_path / "executor_state"
    m.command_state.mkdir()
    m.executor_state.mkdir()
    return m


def test_snapshot_includes_current_and_legacy_ideas(model):
    snapshot = model.build_snapshot(force=True)
    ids = {x["candidate_id"] for x in snapshot["candidates"]}
    assert "C-1" in ids
    assert any(x.startswith("LEGACY-SEED-") for x in ids)
    assert snapshot["counts"]["candidates"] == 2
    assert snapshot["counts"]["legacy_candidates"] == 1
    assert snapshot["edge_state"] == "NO_PROVEN_EDGE"
    assert snapshot["legacy_artifacts"][0]["path"] == "knowledge/research/legacy-note.md"


def test_candidate_journey_links_runs(model):
    detail = model.candidate_detail("C-1")
    assert detail is not None
    assert detail["linked_runs"][0]["run_id"] == "R-1"
    stages = [x["stage"] for x in detail["timeline"]]
    assert "DISCOVERY" in stages
    assert "RUN" in stages
    assert "MECHANISM" in stages


def test_run_detail_exposes_agent_packets(model):
    detail = model.run_detail("R-1")
    paths = {x["path"] for x in detail["artifacts"]}
    assert "knowledge/runs/R-1.json" in paths
    assert "knowledge/runs/agent_packets/R-1/scout.json" in paths


def test_revive_is_immutable_new_request_and_preserves_safety(model):
    first = model.request_revive("C-1", "retry under current gates")
    second = model.request_revive("C-1")
    assert first["request_id"] != second["request_id"]
    assert first["original_candidate_id"] == "C-1"
    assert first["preserve_history"] is True
    assert first["create_new_attempt"] is True
    assert first["mode"] == "FULL_CURRENT_GOVERNED_LIFECYCLE"
    assert first["safety"] == {
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
    }
    assert len(list(model.revive_root.glob("*.json"))) == 2


def test_multisession_task_index_and_failures(model):
    write_json(
        model.command_state / "T-1.json",
        {
            "task_id": "T-1",
            "route_task_id": "SESSION-A",
            "state": "DISPATCHED",
            "created_at": "2026-10-01T12:00:00Z",
        },
    )
    write_json(
        model.executor_state / "T-1.json",
        {
            "task_id": "T-1",
            "status": "PASS",
            "started_at": "2026-10-01T12:00:01Z",
            "finished_at": "2026-10-01T12:00:11Z",
            "exit_code": 0,
        },
    )
    write_json(
        model.command_state / "T-2.json",
        {
            "task_id": "T-2",
            "route_task_id": "SESSION-B",
            "state": "DISPATCHED",
            "created_at": "2026-10-01T12:01:00Z",
        },
    )
    write_json(
        model.executor_state / "T-2.json",
        {
            "task_id": "T-2",
            "status": "FAIL",
            "started_at": "2026-10-01T12:01:01Z",
            "finished_at": "2026-10-01T12:01:05Z",
            "exit_code": 1,
            "error": "synthetic failure",
        },
    )
    snapshot = model.build_snapshot(force=True)
    assert snapshot["counts"]["sessions"] == 2
    assert snapshot["task_metrics"]["success"] == 1
    assert snapshot["task_metrics"]["failure"] == 1
    assert snapshot["errors"][0]["task_id"] == "T-2"
    assert "synthetic failure" in snapshot["errors"][0]["reason"]


def test_artifact_path_traversal_blocked(model):
    with pytest.raises(PermissionError):
        model.artifact("../secret")


def test_artifact_read_is_repo_scoped(model):
    result = model.artifact("knowledge/runs/R-1.json")
    assert result["path"] == "knowledge/runs/R-1.json"
    assert '"run_id": "R-1"' in result["content"]
