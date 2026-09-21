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
