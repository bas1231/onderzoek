from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path
import zlib

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "control/hourly/publication_wake.py"


def load_module():
    spec = importlib.util.spec_from_file_location("publication_wake_test", MODULE_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeContinuation:
    def __init__(self):
        self.calls = []

    def ids_for(self, source_task_id):
        import hashlib
        digest = hashlib.sha256(source_task_id.encode()).hexdigest()[:24]
        return {"continuation_id": "CONT-" + digest}

    def continuation_path(self, data_dir, continuation_id):
        return Path(data_dir) / "continuations" / f"{continuation_id}.json"

    def start_external_continuation(self, **kwargs):
        self.calls.append(kwargs)
        ids = self.ids_for(kwargs["source_task_id"])
        p = self.continuation_path(kwargs["data_dir"], ids["continuation_id"])
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            p.write_text(json.dumps({"state": "CONTINUE_REQUESTED"}) + "\n")
        return {"continuation_id": ids["continuation_id"], "state": "CONTINUE_REQUESTED"}


def configure(mod, tmp_path):
    bridge = tmp_path / "bridge"
    routes = bridge / "routes"
    routes.mkdir(parents=True)
    route_task_id = "ROUTE-TEST-1234"
    (bridge / "autobuild_control_route.json").write_text(json.dumps({
        "schema": "PREDICTION_AUTOBUILD_ROUTE_V1",
        "route_task_id": route_task_id,
    }))
    (routes / f"{route_task_id}.json").write_text(json.dumps({
        "task_id": route_task_id,
        "chat_id": "chat-test-1234",
    }))
    fake = FakeContinuation()
    mod.BRIDGE_DATA = bridge
    mod.ROUTE_CONFIG = bridge / "autobuild_control_route.json"
    mod.ROUTES = routes
    mod.AUDIT_ROOT = tmp_path / "audit"
    mod._load_continuation = lambda: fake
    return fake


def test_denied_and_non_allowlisted_paths_fail_closed(tmp_path):
    mod = load_module()
    for rel in ("knowledge/raw/x.json", "README.md"):
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("{}")
        with pytest.raises(mod.PublicationBlocked):
            mod.ensure_publication(rel, root=tmp_path)


def test_oversized_payload_stays_local_without_continuation(tmp_path):
    mod = load_module()
    fake = configure(mod, tmp_path)
    rel = "knowledge/candidates/large.json"
    target = tmp_path / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    # incompressible enough to exceed the bounded continuation payload
    data = bytes(range(256)) * 40
    target.write_bytes(data)
    result = mod.ensure_publication(rel, root=tmp_path)
    assert result["status"] == "OVERSIZED_LOCAL_ONLY"
    assert result["sha256"]
    assert fake.calls == []


def test_compact_publication_is_deterministic_and_exact(tmp_path):
    mod = load_module()
    fake = configure(mod, tmp_path)
    rel = "knowledge/candidates/test.json"
    raw = b'{"candidate_id":"TEST","status":"RESULT_READY"}\n'
    target = tmp_path / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)

    first = mod.ensure_publication(rel, root=tmp_path)
    second = mod.ensure_publication(rel, root=tmp_path)

    assert first["status"] == "CONTINUATION_CREATED"
    assert first["source_task_id"] == second["source_task_id"]
    assert first["continuation_id"] == second["continuation_id"]
    assert first["new_continuation"] is True
    assert second["new_continuation"] is False

    context = fake.calls[0]["context_message"]
    assert f"path={rel}" in context
    payload_line = next(x for x in context.splitlines() if x.startswith("payload="))
    encoded = payload_line.split("=", 1)[1]
    assert zlib.decompress(base64.b64decode(encoded)) == raw
    assert "create/update exactly this one file" in context
    assert fake.calls[0]["source_kind"] == "GITHUB_PUBLICATION"
