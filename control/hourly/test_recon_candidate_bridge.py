from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUPERVISOR_DIR = HERE.parent / "codex_supervisor"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SUPERVISOR_DIR))

import recon_candidate_bridge as bridge
import candidate_queue
import supervisor
import candidate_dispatch


def _watch_item(status="HUNT", passes=True):
    return {
        "id": "RECON-fixture",
        "candidate_key": "CAND-fixture",
        "observed_at": "2026-10-04T18:00:00+00:00",
        "attack_mode": "CLONE_MUTATE",
        "status": status,
        "claim": "Repeated public evidence suggests a potentially exploitable strategy mechanism; unproven.",
        "quality": {
            "status": "WATCH",
            "economic_context_count": 3,
            "matched_terms": ["strategy"],
            "strong_terms": [],
            "boilerplate_ratio": 0.0,
        },
        "sources": [
            {
                "source_id": "source-a",
                "document_sha256": "a" * 64,
                "term": "strategy",
                "point_in_time": "2026-10-04T18:00:00+00:00",
            }
        ],
        "observation_history": [
            {
                "observed_at": "2026-10-04T18:00:00+00:00",
                "source_id": "source-a",
                "document_sha256": "a" * 64,
                "economic_context_count": 3,
            },
            {
                "observed_at": "2026-10-04T18:05:00+00:00",
                "source_id": "source-b",
                "document_sha256": "b" * 64,
                "economic_context_count": 3,
            },
        ],
        "observation_count": 2,
        "independent_source_count": 2,
        "hunt_gate": {
            "passes": passes,
            "observation_count": 2,
            "independent_source_count": 2,
            "economic_context_count": 3,
            "has_public_trigger": True,
            "has_decisive_test": True,
        },
        "economic_model": {
            "public_trigger": "strategy",
        },
        "falsification": {
            "next_decisive_test": "Establish out-of-sample predictiveness and executable net economics.",
            "required_data": [],
            "specialist_route": ["microstructure"],
        },
        "snippet": "strategy market trading order price liquidity",
    }


def _write_watchlist(root: Path, items):
    path = root / "knowledge/recon/watchlist.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"version": 1, "items": items}) + "\n")


def test_hunt_creates_exactly_one_candidate_and_is_idempotent(tmp_path):
    _write_watchlist(tmp_path, [_watch_item()])
    stamp = "2026-10-04T20:00:00+00:00"

    first, _ = bridge.promote("hourly-test", root=tmp_path, timestamp=stamp)
    assert first["created_count"] == 1
    assert first["skipped_existing_count"] == 0

    files = list((tmp_path / "knowledge/candidates").glob("*.json"))
    assert len(files) == 1
    candidate = json.loads(files[0].read_text())
    assert candidate["queue_status"] == "NEEDS_DIRECTOR"
    assert candidate["decision"] == "UNPROVEN"
    assert candidate["scientific_status"] == "NO_PROVEN_EDGE"
    assert candidate["live_trading"] is False
    assert candidate["paid_actions"] is False
    assert candidate["wallet_actions"] is False
    assert candidate["origin_recon_candidate_key"] == "CAND-fixture"

    second, _ = bridge.promote("hourly-test-2", root=tmp_path, timestamp=stamp)
    assert second["created_count"] == 0
    assert second["skipped_existing_count"] == 1
    assert len(list((tmp_path / "knowledge/candidates").glob("*.json"))) == 1


def test_watch_or_failed_hunt_gate_does_not_create_candidate(tmp_path):
    _write_watchlist(tmp_path, [_watch_item(status="WATCH"), _watch_item(status="HUNT", passes=False)])
    result, _ = bridge.promote("hourly-test", root=tmp_path, timestamp="2026-10-04T20:00:00+00:00")
    assert result["created_count"] == 0
    assert result["ineligible_count"] == 2
    assert not (tmp_path / "knowledge/candidates").exists()


def test_created_candidate_enters_existing_queue_and_dispatch(tmp_path, monkeypatch):
    _write_watchlist(tmp_path, [_watch_item()])
    result, _ = bridge.promote("hourly-test", root=tmp_path, timestamp="2026-10-04T20:00:00+00:00")
    cid = result["created"][0]["candidate_id"]

    monkeypatch.setattr(candidate_queue, "ROOT", tmp_path)
    monkeypatch.setattr(candidate_queue, "CANDIDATES", tmp_path / "knowledge/candidates")
    monkeypatch.setattr(candidate_queue, "RUNS", tmp_path / "knowledge/runs")
    queue = candidate_queue.build_queue(write_candidates=False)
    row = next(x for x in queue["queue"] if x["candidate_id"] == cid)
    assert row["queue_status"] == "NEEDS_DIRECTOR"
    assert row["priority"] == "P2"

    runtime = tmp_path / "knowledge/codex_runtime"
    s = supervisor.Supervisor(runtime, worker=lambda *args: 0)
    with s.locked():
        task = candidate_dispatch.select_task(s, tmp_path)
    assert task is not None
    assert task["candidate_id"] == cid
    assert task["candidate_dispatch"] is True
    assert task["task_class"] == "research_review"
    assert "scientific_status=NO_PROVEN_EDGE" in task["prompt"]
