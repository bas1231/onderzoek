import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path.cwd()


def load_module():
    path = ROOT / "control/hourly/git_ai_exchange.py"
    spec = importlib.util.spec_from_file_location("git_ai_exchange_v14_test", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def git(cwd, *args):
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def make_repo(tmp_path):
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    remote.mkdir()
    work.mkdir()
    git(remote, "init", "--bare")
    git(work, "init")
    git(work, "config", "user.email", "test@example.invalid")
    git(work, "config", "user.name", "V14 Test")
    (work / "seed.txt").write_text("seed\n", encoding="utf-8")
    git(work, "add", "seed.txt")
    git(work, "commit", "-m", "seed")
    git(work, "branch", "ai/runtime-exchange")
    git(work, "remote", "add", "origin", str(remote))
    git(work, "push", "origin", "ai/runtime-exchange")
    return work, remote


def request():
    return {
        "schema": "PVA_AI_EXCHANGE_REQUEST_V1",
        "run_id": "hourly-20260921T210000+0200",
        "request_sha256": "a" * 64,
        "work_items": [{"agent_id": "settlement"}],
    }


def test_publish_is_append_only_and_does_not_touch_worktree(tmp_path, monkeypatch):
    mod = load_module()
    work, _ = make_repo(tmp_path)
    monkeypatch.setattr(mod, "ROOT", work)
    monkeypatch.setattr(
        mod,
        "load_module",
        lambda *args, **kwargs: SimpleNamespace(validate_request=lambda value: value),
    )

    before = git(work, "status", "--porcelain")
    first = mod.publish_request(request())
    after = git(work, "status", "--porcelain")

    assert first["status"] == "PUBLISHED"
    assert first["live_trading"] is False
    assert first["paid_actions"] is False
    assert first["wallet_actions"] is False
    assert before == after == ""

    second = mod.publish_request(request())
    assert second["status"] == "ALREADY_PUBLISHED"
    assert git(work, "status", "--porcelain") == ""


def test_conflicting_existing_request_fails_closed(tmp_path, monkeypatch):
    mod = load_module()
    work, _ = make_repo(tmp_path)
    monkeypatch.setattr(mod, "ROOT", work)
    monkeypatch.setattr(
        mod,
        "load_module",
        lambda *args, **kwargs: SimpleNamespace(validate_request=lambda value: value),
    )

    mod.publish_request(request())
    conflict = json.loads(json.dumps(request()))
    conflict["work_items"][0]["agent_id"] = "algebra"
    with pytest.raises(mod.GitExchangeError, match="conflicting request"):
        mod.publish_request(conflict)


def test_response_envelope_requires_request_hash_and_matching_run():
    mod = load_module()
    run_id = "hourly-20260921T210000+0200"
    response = {
        "schema": "PVA_AI_RESPONSE_V1",
        "run_id": run_id,
    }
    envelope = {
        "schema": "PVA_AI_EXCHANGE_RESPONSE_V1",
        "run_id": run_id,
        "request_sha256": "b" * 64,
        "response": response,
    }
    resolved, payload, request_sha = mod._validate_envelope(envelope)
    assert resolved == run_id
    assert payload is response
    assert request_sha == "b" * 64

    bad = json.loads(json.dumps(envelope))
    bad["response"]["run_id"] = "hourly-20990101T000000+0000"
    with pytest.raises(mod.GitExchangeError, match="run mismatch"):
        mod._validate_envelope(bad)


def test_e004_quarantine_requires_exact_historical_blob_and_validation_signature(monkeypatch):
    mod = load_module()
    legacy_path = "ai_exchange/responses/hourly-20260922T150000+0200.json"
    legacy_sha = "95f6fa87c56604b71520d0cdc321f300c431f494"

    class ValidationError(Exception):
        pass

    monkeypatch.setattr(mod, "_blob_sha", lambda ref, path: legacy_sha)
    record = mod._historical_quarantine_record(
        "exchange-ref",
        legacy_path,
        ValidationError("invalid agent_id: recon_scout"),
    )
    assert record is not None
    assert record["blob_sha"] == legacy_sha
    assert record["reason"] == "PRE_E001_LEGACY_ROLE_CONTRACT"

    monkeypatch.setattr(mod, "_blob_sha", lambda ref, path: "0" * 40)
    assert mod._historical_quarantine_record(
        "exchange-ref",
        legacy_path,
        ValidationError("invalid agent_id: recon_scout"),
    ) is None

    monkeypatch.setattr(mod, "_blob_sha", lambda ref, path: legacy_sha)
    assert mod._historical_quarantine_record(
        "exchange-ref",
        legacy_path,
        ValidationError("different validation failure"),
    ) is None


def test_e004_ingest_applies_current_response_without_historical_error_pollution(
    tmp_path,
    monkeypatch,
):
    mod = load_module()
    monkeypatch.setattr(mod, "ROOT", tmp_path)

    legacy_run = "hourly-20260922T150000+0200"
    current_run = "hourly-20260923T100000+0200"
    legacy_path = f"ai_exchange/responses/{legacy_run}.json"
    current_path = f"ai_exchange/responses/{current_run}.json"
    legacy_sha = "95f6fa87c56604b71520d0cdc321f300c431f494"
    legacy_request_sha = "a" * 64
    current_request_sha = "b" * 64

    request_dir = tmp_path / "knowledge/ai_exchange/requests"
    request_dir.mkdir(parents=True)
    for run_id, request_sha in (
        (legacy_run, legacy_request_sha),
        (current_run, current_request_sha),
    ):
        (request_dir / f"{run_id}.json").write_text(
            json.dumps({"request_sha256": request_sha}),
            encoding="utf-8",
        )

    def envelope(run_id, request_sha):
        return json.dumps({
            "schema": "PVA_AI_EXCHANGE_RESPONSE_V1",
            "run_id": run_id,
            "request_sha256": request_sha,
            "response": {
                "schema": "PVA_AI_RESPONSE_V1",
                "run_id": run_id,
            },
        })

    raw_by_path = {
        legacy_path: envelope(legacy_run, legacy_request_sha),
        current_path: envelope(current_run, current_request_sha),
    }

    class ValidationError(Exception):
        pass

    class Receiver:
        @staticmethod
        def receive(payload):
            run_id = payload["run_id"]
            if run_id == legacy_run:
                raise ValidationError("invalid agent_id: recon_scout")

            final_response = tmp_path / "knowledge/runs" / f"{run_id}-ai-response.json"
            receipt = tmp_path / "knowledge/runs" / f"{run_id}-ai-response-receipt.json"
            orchestration = (
                tmp_path
                / "knowledge/runs/agent_packets"
                / run_id
                / "_orchestration.json"
            )
            final_response.parent.mkdir(parents=True, exist_ok=True)
            orchestration.parent.mkdir(parents=True, exist_ok=True)
            final_response.write_text("{}\n", encoding="utf-8")
            receipt.write_text("{}\n", encoding="utf-8")
            orchestration.write_text("{}\n", encoding="utf-8")
            return {
                "already_applied": False,
                "response_ref": str(final_response),
                "receipt_ref": str(receipt),
                "role_statuses": {"discovery": "COMPLETED"},
            }

    contract = SimpleNamespace(validate_request=lambda value: value)

    def fake_load_module(name, path):
        if "contract" in name:
            return contract
        if "receiver" in name:
            return Receiver
        raise AssertionError(name)

    monkeypatch.setattr(mod, "fetch_exchange", lambda: "exchange-ref")
    monkeypatch.setattr(mod, "_response_paths", lambda ref: [legacy_path, current_path])
    monkeypatch.setattr(mod, "_show", lambda ref, path: raw_by_path[path])
    monkeypatch.setattr(
        mod,
        "_blob_sha",
        lambda ref, path: legacy_sha if path == legacy_path else None,
    )
    monkeypatch.setattr(mod, "load_module", fake_load_module)

    result = mod.ingest_remote_responses()

    assert result["status"] == "APPLIED"
    assert result["ok"] is True
    assert result["errors"] == []
    assert len(result["quarantined"]) == 1
    assert result["quarantined"][0]["path"] == legacy_path
    assert result["quarantined"][0]["reason"] == "PRE_E001_LEGACY_ROLE_CONTRACT"
    assert [item["run_id"] for item in result["applied"]] == [current_run]
    assert result["applied"][0]["recovery_retry"] is False
