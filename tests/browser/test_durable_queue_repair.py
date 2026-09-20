from pathlib import Path


SOURCE = Path(
    "control/browser_extension/content.js"
).read_text(encoding="utf-8")


def test_flush_function_exists():
    assert "async function flushDurableQueue()" in SOURCE


def test_flush_loads_persisted_queue():
    start = SOURCE.index(
        "async function flushDurableQueue()"
    )
    body = SOURCE[start:start + 7000]

    assert "await loadDurableQueue()" in body
    assert '"/discover"' in body
    assert '"/enqueue"' in body


def test_flush_accepts_existing_task_as_idempotent():
    start = SOURCE.index(
        "async function flushDurableQueue()"
    )
    body = SOURCE[start:start + 7000]

    assert "response.status === 409" in body
    assert '"task_id already exists"' in body


def test_flush_marks_and_removes_only_after_acceptance():
    start = SOURCE.index(
        "async function flushDurableQueue()"
    )
    body = SOURCE[start:start + 7000]

    mark = body.index(
        "await markTaskProcessed(taskId)"
    )
    remove = body.index(
        "await removeDurableEnvelope(taskId)",
        mark,
    )

    assert remove > mark


def test_failure_is_retained_with_attempt_metadata():
    start = SOURCE.index(
        "async function flushDurableQueue()"
    )
    body = SOURCE[start:start + 7000]

    assert "record.attempts" in body
    assert "record.lastError" in body
    assert "await saveDurableQueue(queue)" in body


def test_normal_enqueue_removes_durable_item():
    marker = (
        "await markTaskProcessed(taskId);\n"
        "              processed.add(taskId);\n"
        "              await removeDurableEnvelope(taskId);"
    )

    assert marker in SOURCE


def test_ai_delivery_remains_present():
    assert "async function pollAiOutbox()" in SOURCE
    assert '"/ai-outbox"' in SOURCE
    assert '"/ai-ack"' in SOURCE
