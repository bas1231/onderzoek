from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import supervisor


def _task():
    prompt = "quota retry regression"
    return {
        "task_id": "TEST-USAGE-RETRY",
        "task_class": "research_review",
        "priority": 100,
        "expected_value": 10,
        "estimated_reasoning_cost": 1,
        "created_at": "2026-10-04T00:00:00+00:00",
        "prompt": prompt,
        "input_sha256": supervisor.digest(prompt.encode()),
    }


def test_usage_limit_retries_same_task_after_15_minutes(tmp_path):
    now = [1000.0]
    calls = []

    def clock():
        return now[0]

    def worker(task, thread, folder, lock_fd):
        calls.append(task["task_id"])
        events = [
            {"type": "thread.started", "thread_id": "thread-test"},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "done"}},
            {"type": "turn.completed"},
        ]
        (folder / "events.jsonl").write_text(
            "".join(json.dumps(event) + "\n" for event in events)
        )
        return 0

    s = supervisor.Supervisor(tmp_path, worker=worker, clock=clock)
    task = _task()
    first_run = tmp_path / "runs" / "TEST-USAGE-RETRY-1-seed"
    first_run.mkdir(parents=True)

    with s.locked():
        s.db.execute(
            "insert into tasks(id,body,status,attempt,run) values(?,?,?,?,?)",
            (
                task["task_id"],
                json.dumps(task, sort_keys=True),
                "RUNNING",
                1,
                str(first_run.relative_to(tmp_path)),
            ),
        )
        s.apply_result(task, 1, first_run, "USAGE_LIMIT", None)
        row = s.db.execute(
            "select status from tasks where id=?", (task["task_id"],)
        ).fetchone()
        transition = s.db.execute(
            "select retry-stamp from transitions where task=? and reason='USAGE_LIMIT' order by seq desc limit 1",
            (task["task_id"],),
        ).fetchone()

    assert row == ("PAUSED_USAGE_LIMIT",)
    assert transition == (supervisor.USAGE_LIMIT_RETRY_SECONDS,)
    assert supervisor.USAGE_LIMIT_RETRY_SECONDS == 900

    now[0] = 1899.0
    paused = s.tick()
    assert paused["state"] == "PAUSED_USAGE_LIMIT"
    assert calls == []

    now[0] = 1900.0
    completed = s.tick()
    assert completed["state"] == "COMPLETE"
    assert calls == [task["task_id"]]

    with s.locked():
        row = s.db.execute(
            "select status,attempt from tasks where id=?", (task["task_id"],)
        ).fetchone()
    assert row == ("COMPLETE", 2)


def test_legacy_five_hour_usage_pause_is_effectively_capped(tmp_path):
    now = [1899.0]
    calls = []

    def clock():
        return now[0]

    def worker(task, thread, folder, lock_fd):
        calls.append(task["task_id"])
        events = [
            {"type": "thread.started", "thread_id": "thread-legacy"},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "done"}},
            {"type": "turn.completed"},
        ]
        (folder / "events.jsonl").write_text(
            "".join(json.dumps(event) + "\n" for event in events)
        )
        return 0

    s = supervisor.Supervisor(tmp_path, worker=worker, clock=clock)
    task = _task()
    task["task_id"] = "TEST-USAGE-LEGACY"
    first_run = tmp_path / "runs" / "TEST-USAGE-LEGACY-1-seed"
    first_run.mkdir(parents=True)

    with s.locked():
        s.db.execute(
            "insert into tasks(id,body,status,attempt,run) values(?,?,?,?,?)",
            (
                task["task_id"],
                json.dumps(task, sort_keys=True),
                "PAUSED_USAGE_LIMIT",
                1,
                str(first_run.relative_to(tmp_path)),
            ),
        )
        s.db.execute(
            "insert into transitions(state,task,reason,attempt,checkpoint,next_action,stamp,retry) "
            "values(?,?,?,?,?,?,?,?)",
            (
                "PAUSED_USAGE_LIMIT",
                task["task_id"],
                "USAGE_LIMIT",
                1,
                str(first_run.relative_to(tmp_path)),
                "resume_same_task",
                1000.0,
                19000.0,
            ),
        )

    paused = s.tick()
    assert paused["state"] == "PAUSED_USAGE_LIMIT"
    assert paused["retry_at"] == 1900.0
    assert calls == []

    now[0] = 1900.0
    completed = s.tick()
    assert completed["state"] == "COMPLETE"
    assert calls == [task["task_id"]]

    with s.locked():
        persisted = s.db.execute(
            "select retry from transitions where task=? and reason='USAGE_LIMIT' order by seq limit 1",
            (task["task_id"],),
        ).fetchone()
        row = s.db.execute(
            "select status,attempt from tasks where id=?", (task["task_id"],)
        ).fetchone()
    assert persisted == (19000.0,)
    assert row == ("COMPLETE", 2)
