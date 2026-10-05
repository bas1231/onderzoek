import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control/hourly"))
sys.path.insert(0, str(ROOT / "control/codex_supervisor"))

import candidate_reporting as r
import model_quality_gate as q


def write_overlay(runtime, name, value):
    root = runtime / "candidate_states"
    root.mkdir(parents=True, exist_ok=True)
    (root / name).write_text(json.dumps(value))


def base_overlay(stamp, version):
    return {
        "candidate_id": "CANDIDATE-1",
        "decision_timestamp": stamp,
        "queue_status": "NEEDS_DIRECTOR",
        "source_hashes": {"knowledge/candidates/CANDIDATE-1.json": f"hash-{version}"},
        "originating_task_id": f"TASK-{version}",
        "completion_hash": f"completion-{version}",
        "validation_hash": None,
        "finding": f"finding-{version}",
        "next_action": f"next-{version}",
        "candidate_snapshot": {"candidate_id": "CANDIDATE-1", "version": version},
        "referenced_evidence": {"version": version},
    }


def queue():
    return {
        "queue": [{
            "candidate_id": "CANDIDATE-1",
            "queue_status": "NEEDS_DIRECTOR",
            "next_decisive_test": "next",
        }]
    }


def test_reporting_does_not_carry_old_approvals_into_new_candidate_version(tmp_path):
    runtime = tmp_path / "runtime"
    old = base_overlay(1, 1)
    old["astra_reviews"] = {
        "PREBUILD": {
            "decision": "APPROVE",
            "binding_sha256": r._review_binding(old, "PREBUILD"),
            "ref": "knowledge/reviews/astra/old-prebuild.json",
        },
        "PREMEASUREMENT": {
            "decision": "APPROVE",
            "binding_sha256": r._review_binding(old, "PREMEASUREMENT"),
            "ref": "knowledge/reviews/astra/old-premeasurement.json",
        },
    }
    old["measurement_authorization"] = {
        "authorized": True,
        "scope": "READ_ONLY_PROSPECTIVE_MARKET_DATA",
        "order_submission": False,
        "astra_premeasurement_review_ref": "knowledge/reviews/astra/old-premeasurement.json",
    }
    write_overlay(runtime, "old.json", old)

    current = base_overlay(2, 2)
    write_overlay(runtime, "current.json", current)

    row = r.summarize(queue(), runtime)["candidates"][0]
    assert row["astra_prebuild"] is None
    assert row["astra_premeasurement"] is None
    assert row["measurement_scope"] is None
    assert row["measurement_order_submission"] is None


def test_reporting_shows_only_current_bound_reviews_and_authorization(tmp_path):
    runtime = tmp_path / "runtime"
    current = base_overlay(2, 2)
    prebuild_ref = "knowledge/reviews/astra/current-prebuild.json"
    premeasurement_ref = "knowledge/reviews/astra/current-premeasurement.json"
    current["astra_reviews"] = {
        "PREBUILD": {
            "decision": "APPROVE",
            "binding_sha256": r._review_binding(current, "PREBUILD"),
            "ref": prebuild_ref,
        },
        "PREMEASUREMENT": {
            "decision": "APPROVE",
            "binding_sha256": r._review_binding(current, "PREMEASUREMENT"),
            "ref": premeasurement_ref,
        },
    }
    current["measurement_authorization"] = {
        "authorized": True,
        "scope": "READ_ONLY_PROSPECTIVE_MARKET_DATA",
        "order_submission": False,
        "astra_premeasurement_review_ref": premeasurement_ref,
    }
    write_overlay(runtime, "current.json", current)

    row = r.summarize(queue(), runtime)["candidates"][0]
    assert row["astra_prebuild"] == "APPROVE"
    assert row["astra_premeasurement"] == "APPROVE"
    assert row["measurement_scope"] == "READ_ONLY_PROSPECTIVE_MARKET_DATA"
    assert row["measurement_order_submission"] is False


def test_reporting_hides_review_with_stale_binding_even_in_latest_overlay(tmp_path):
    runtime = tmp_path / "runtime"
    current = base_overlay(2, 2)
    current["astra_reviews"] = {
        "PREBUILD": {
            "decision": "APPROVE",
            "binding_sha256": "0" * 64,
            "ref": "knowledge/reviews/astra/stale.json",
        }
    }
    write_overlay(runtime, "current.json", current)

    row = r.summarize(queue(), runtime)["candidates"][0]
    assert row["astra_prebuild"] is None


def test_reporting_binding_matches_canonical_astra_gate():
    current = base_overlay(2, 2)
    assert r._review_binding(current, "PREBUILD") == q.review_binding(current, "PREBUILD")
    assert r._review_binding(current, "PREMEASUREMENT") == q.review_binding(current, "PREMEASUREMENT")
