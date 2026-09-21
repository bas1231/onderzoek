import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace


ROOT = Path.cwd()


def load_module():
    path = ROOT / "control/hourly/hourly_wake.py"
    spec = importlib.util.spec_from_file_location("hourly_wake_git_v14_test", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def install_fake_runtime(mod, tmp_path, monkeypatch, publish_status):
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    now = datetime.now().astimezone()
    run_id = mod.current_run_id(now)
    bundle = tmp_path / "knowledge/runs" / f"{run_id}-ai-work-bundle.json"
    bundle.parent.mkdir(parents=True)
    bundle.write_text(json.dumps({"schema": "PVA_AI_WORK_BUNDLE_V1"}))

    local_request = tmp_path / "knowledge/ai_exchange/requests" / f"{run_id}.json"
    local_request.parent.mkdir(parents=True)

    contract = SimpleNamespace(
        build_and_write=lambda value: (
            {"run_id": run_id, "work_items": [{"agent_id": "settlement"}]},
            local_request,
        )
    )
    transport = SimpleNamespace(
        safe_ingest_remote_responses=lambda: {
            "ok": True,
            "status": "NO_APPLICABLE_RESPONSES",
        },
        safe_publish_request=lambda request: {
            "ok": publish_status in {"PUBLISHED", "ALREADY_PUBLISHED", "NO_WORK"},
            "status": publish_status,
            "run_id": run_id,
            "error": "synthetic transport failure" if publish_status == "TRANSPORT_UNAVAILABLE" else None,
        },
    )

    def fake_loader(name, path):
        if path.name == "ai_work_exchange.py":
            return contract
        if path.name == "git_ai_exchange.py":
            return transport
        raise AssertionError(path)

    monkeypatch.setattr(mod, "load_module", fake_loader)
    return run_id


def test_git_delivery_does_not_wake_browser(tmp_path, monkeypatch):
    mod = load_module()
    run_id = install_fake_runtime(mod, tmp_path, monkeypatch, "PUBLISHED")
    monkeypatch.setattr(
        mod,
        "browser_fallback",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("browser fallback called")),
    )

    assert mod.main() == 0
    status = json.loads(
        (tmp_path / "knowledge/ai_exchange/status" / f"{run_id}.json").read_text()
    )
    assert status["publish"]["status"] == "PUBLISHED"
    assert status["browser_bridge_required"] is False
    assert status["browser_fallback"]["used"] is False


def test_no_work_does_not_wake_browser(tmp_path, monkeypatch):
    mod = load_module()
    install_fake_runtime(mod, tmp_path, monkeypatch, "NO_WORK")
    monkeypatch.setattr(
        mod,
        "browser_fallback",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("browser fallback called")),
    )
    assert mod.main() == 0


def test_transport_failure_uses_browser_only_as_fallback(tmp_path, monkeypatch):
    mod = load_module()
    run_id = install_fake_runtime(mod, tmp_path, monkeypatch, "TRANSPORT_UNAVAILABLE")
    calls = []
    monkeypatch.setattr(
        mod,
        "browser_fallback",
        lambda now, rid, reason: calls.append((rid, reason)) or {
            "used": True,
            "reason": reason,
        },
    )

    assert mod.main() == 0
    assert calls and calls[0][0] == run_id
    status = json.loads(
        (tmp_path / "knowledge/ai_exchange/status" / f"{run_id}.json").read_text()
    )
    assert status["browser_fallback"]["used"] is True
    assert status["live_trading"] is False
    assert status["paid_actions"] is False
    assert status["wallet_actions"] is False
