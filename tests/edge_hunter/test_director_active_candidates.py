import importlib.util
import json
from pathlib import Path

import yaml


def load_director():
    path = Path(__file__).resolve().parents[2] / "control/edge_hunter/director.py"
    spec = importlib.util.spec_from_file_location("edge_hunter_director_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_active_candidates_are_included_in_edge_packet(tmp_path):
    director = load_director()

    (tmp_path / "knowledge/runs").mkdir(parents=True)
    (tmp_path / "knowledge/candidates").mkdir(parents=True)
    (tmp_path / "candidates/active").mkdir(parents=True)
    (tmp_path / "control/edge_hunter").mkdir(parents=True)

    run_id = "test-run"
    (tmp_path / "knowledge/runs" / f"{run_id}.json").write_text(
        json.dumps({"run_id": run_id}) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "knowledge/runs" / f"{run_id}-routing.json").write_text(
        json.dumps({}) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "control/edge_hunter/lane_registry.json").write_text(
        json.dumps({"lanes": {}}) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "knowledge/candidates/legacy.json").write_text(
        json.dumps({"candidate_id": "LEGACY-001", "status": "UNPROVEN"}) + "\n",
        encoding="utf-8",
    )

    active = {
        "schema_version": 1,
        "candidate_id": "PM-NR-V2-CONVERT-001",
        "status": "NEEDS_DIRECTOR",
        "economic_status": "NO_PROVEN_EDGE",
    }
    (tmp_path / "candidates/active/PM-NR-V2-CONVERT-001.yaml").write_text(
        yaml.safe_dump(active, sort_keys=True),
        encoding="utf-8",
    )

    director.ROOT = tmp_path
    director.LANE_REGISTRY = tmp_path / "control/edge_hunter/lane_registry.json"
    director.ACTIVE_CANDIDATE_DIR = tmp_path / "candidates/active"

    out = director.prepare(run_id)
    packet = json.loads(out.read_text(encoding="utf-8"))

    assert packet["candidates"][0]["candidate_id"] == "LEGACY-001"
    assert len(packet["active_candidates"]) == 1
    row = packet["active_candidates"][0]
    assert row["candidate_id"] == "PM-NR-V2-CONVERT-001"
    assert row["status"] == "NEEDS_DIRECTOR"
    assert row["economic_status"] == "NO_PROVEN_EDGE"
    assert row["_source_path"] == "candidates/active/PM-NR-V2-CONVERT-001.yaml"


def test_missing_active_candidate_directory_is_safe(tmp_path):
    director = load_director()
    director.ROOT = tmp_path
    director.ACTIVE_CANDIDATE_DIR = tmp_path / "candidates/active"
    assert director.load_active_candidates() == []
