"""Gewenst gedrag; deze tests moeten rood blijven zolang de defecten bestaan."""
import json
from pathlib import Path
import subprocess
import sys
import pytest


@pytest.fixture(scope="module")
def observed():
    return json.loads(subprocess.check_output([sys.executable, "knowledge/codex_audit/evidence/reproduce_defects.py"], text=True))


def test_receipt_never_precedes_response_body(observed):
    assert all(not row["backdated"] for row in observed["recorders"])


def test_invalid_economics_never_passes_proof(observed):
    assert all(not row["accepted"] for row in observed["proof_gate"])


def test_successful_route_is_persisted(observed):
    row = observed["corrupt_route"]
    assert row["rejected"] or row["persisted_route"] == row["reported_route"]


def test_nonobject_payload_gets_explicit_400(observed):
    assert observed["nonobject_json"] == {"exception": None, "http_replies": [400]}


def test_timeout_writes_result(observed):
    assert observed["executor_timeout"]["result_written"]


def test_internal_coverage_hole_is_unproven(observed):
    assert observed["coverage_hole"]["status"] == "UNPROVEN_REACTION"


def test_no_executable_book_is_unproven(observed):
    assert observed["empty_executable_book"]["status"] == "UNPROVEN_REACTION"


def test_nonprospective_target_is_excluded(observed):
    assert observed["negative_lead_cross_config"]["eligible_rows"] == 0


def test_unsent_user_draft_is_preserved():
    row = json.loads(subprocess.check_output(["node", "knowledge/codex_audit/evidence/composer_reproduction.js"], text=True))
    assert row["remaining"] == row["initial_draft"] and row["sent"] == []
