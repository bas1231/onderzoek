from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def text(path):
    return (ROOT / path).read_text(
        encoding="utf-8"
    )


def test_binary_safe_file_transport():
    src = text(
        "control/browser_bridge_core.py"
    )

    assert "content_b64" in src
    assert "base64.b64decode" in src
    assert "decoded_content()" in src


def test_direct_task_compatibility():
    src = text(
        "control/browser_extension/content.js"
    )

    assert "envelope.task_id" in src
    assert "directTask.task_id" in src


def test_discovery_window_hardened():
    src = text(
        "control/browser_extension/content.js"
    )

    assert "allNodes.length > 100" in src
    assert "allNodes.slice(-100)" in src
    assert "rawText.length > 1000000" in src


def test_normal_tick_flushes_durable_tasks():
    src = text(
        "control/browser_extension/content.js"
    )

    expected = (
        "scanForTasks();\n"
        "      flushDurableQueue();\n"
        "      flushPendingResultAcks();"
    )

    assert expected in src


def test_explicit_provenance_fields():
    src = text(
        "control/browser_extension/content.js"
    )

    assert "task_source_commit:" in src
    assert "execution_start_head:" in src
    assert "result_source_commit:" in src
    assert "delivery_head:" in src


def test_ack_reconciliation():
    src = text(
        "control/browser_bridge_core.py"
    )

    assert "recovered_acks = []" in src
    assert "load_record as lifecycle_load" in src


def test_newest_results_and_incidents_first():
    src = text(
        "control/browser_bridge_core.py"
    )

    assert (
        "for priority_task_id in reversed(bridge_tasks):"
        in src
    )

    incident_pos = src.index(
        "incident_paths = sorted("
    )

    assert (
        "reverse=True"
        in src[
            incident_pos:
            incident_pos + 300
        ]
    )
