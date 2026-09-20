
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import importlib
import json
import sys


def test_outbox_prefers_result_then_incident(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[2]
    control = root / "control"

    if str(control) not in sys.path:
        sys.path.insert(0, str(control))

    bb = importlib.import_module("browser_bridge")

    results = tmp_path / "results"
    result_dir = results / "TASK-RESULT-1"
    result_dir.mkdir(parents=True)
    (result_dir / "RESULT.json").write_text(
        json.dumps(
            {
                "task_id": "TASK-RESULT-1",
                "status": "completed",
            }
        ),
        encoding="utf-8",
    )
    (result_dir / "stdout.log").write_text(
        "ok",
        encoding="utf-8",
    )
    (result_dir / "stderr.log").write_text(
        "",
        encoding="utf-8",
    )

    home = tmp_path / "home"
    incident_dir = (
        home
        / ".local"
        / "state"
        / "prediction-research"
        / "incidents"
    )
    incident_dir.mkdir(parents=True)
    (incident_dir / "demo.json").write_text(
        json.dumps(
            {
                "deliver_to_chat": True,
                "reason": "DEMO_INCIDENT",
                "detail": "demo",
            }
        ),
        encoding="utf-8",
    )

    state = {
        "bridge_tasks": ["TASK-RESULT-1"],
        "acked": [],
    }

    monkeypatch.setattr(bb, "RESULTS", results)
    monkeypatch.setattr(bb, "load_state", lambda: state)
    monkeypatch.setattr(
        bb,
        "save_state",
        lambda new_state: None,
    )
    monkeypatch.setattr(
        bb,
        "lifecycle_update",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        bb,
        "git",
        lambda *args, **kwargs: SimpleNamespace(
            stdout="abc123\n"
        ),
    )

    with patch.object(
        bb.Path,
        "home",
        return_value=home,
    ):
        first = bb.next_outbox_item()
        second = bb.next_outbox_item()

    assert first["task_id"] == "TASK-RESULT-1"
    assert second["task_id"].startswith("INCIDENT-")
    assert state["outbox_prefer_incident"] is False
