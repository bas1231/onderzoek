from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
import textwrap
import time
import urllib.request

ROOT = Path.cwd()
BRIDGE = ROOT / "control/browser_bridge.py"
TEST = ROOT / "tests/bridge/test_control_auto_continue.py"
LEDGER = ROOT / "control/BRIDGE_INCIDENT_LEDGER.md"

HELPERS = r'''
def _control_continue_result(task_id: str) -> dict | None:
    result_file = RESULTS / task_id / "RESULT.json"

    if not result_file.exists():
        return None

    try:
        result = json.loads(
            result_file.read_text(encoding="utf-8")
        )
    except Exception:
        return None

    if result.get("status") not in {"completed", "failed"}:
        return None

    if result.get("task_class") not in {
        "research",
        "infrastructure",
    }:
        return None

    return result


def _control_continue_item(
    source_task_id: str,
    reason: str,
) -> dict | None:
    result = _control_continue_result(source_task_id)

    if result is None:
        return None

    safe_source = "".join(
        ch if (ch.isalnum() or ch in "._:-") else "_"
        for ch in source_task_id
    )[:120]

    wake_id = (
        "control-continue-" + safe_source
    )[:150]

    return {
        "kind": "AI_WORK_BUNDLE",
        "schema": "PVA_CONTROL_CONTINUE_V1",
        "task_id": wake_id,
        "run_id": "control-" + safe_source,
        "bundle_ref": (
            "control/results/"
            + source_task_id
            + "/RESULT.json"
        ),
        "bundle": {
            "schema": "PVA_CONTROL_CONTINUE_BUNDLE_V1",
            "source_task_id": source_task_id,
            "source_result": {
                "status": result.get("status"),
                "task_class": result.get("task_class"),
                "hypothesis_id": result.get("hypothesis_id"),
                "exit_code": result.get("exit_code"),
                "source_commit": result.get("source_commit"),
            },
            "wake_reason": reason,
            "continuation_policy": {
                "do_not_wait_for_manual_continue": True,
                "inspect_source_of_truth_first": True,
                "advance_after_pass": True,
                "diagnose_and_repair_after_failure": True,
                "respect_work_cadence": True,
                "no_live_trading": True,
                "no_paid_actions": True,
                "no_wallet_actions": True,
                "no_openai_api": True,
            },
        },
        "response_contract": {
            "schema": "PVA_CONTROL_CONTINUE_RESPONSE_V1",
            "direct_execution_allowed": False,
            "economic_conclusion": "NO_PROVEN_EDGE",
        },
        "instruction": (
            "Continue the currently authorized Prediction research and "
            "control-plane work autonomously from this completed bridge "
            "result. Inspect the returned result and repository state first. "
            "If it passed, advance to the next planned gate or research task. "
            "If it failed, diagnose and repair it. Do not stop merely to wait "
            "for the user to say continue. If a work-cadence cooldown or an "
            "authorization boundary blocks further work, report that instead. "
            "Never perform live trading, paid actions, wallet actions or "
            "OpenAI API calls."
        ),
        "guardrails": {
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "openai_api": False,
            "direct_executor_route": False,
        },
    }


def _queue_control_continue(
    state: dict,
    source_task_id: str,
    reason: str,
) -> bool:
    seen = state.setdefault(
        "control_continue_seen",
        [],
    )

    if source_task_id in seen:
        return False

    item = _control_continue_item(
        source_task_id,
        reason,
    )

    if item is None:
        return False

    queue = state.setdefault(
        "control_continue_queue",
        [],
    )
    queue.append(item)
    seen.append(source_task_id)

    while len(queue) > 100:
        queue.pop(0)

    while len(seen) > 500:
        seen.pop(0)

    return True


def _sync_recent_ack_stall_fallbacks(state: dict) -> bool:
    incident_dir = (
        Path.home()
        / ".local"
        / "state"
        / "prediction-research"
        / "incidents"
    )

    if not incident_dir.exists():
        return False

    now = time.time()
    changed = False

    incident_paths = sorted(
        incident_dir.glob("*__CHAT_ACK_STALL.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )[:20]

    for incident_path in incident_paths:
        try:
            incident = json.loads(
                incident_path.read_text(encoding="utf-8")
            )
        except Exception:
            continue

        if incident.get("reason") != "CHAT_ACK_STALL":
            continue

        last_seen = float(
            incident.get("last_seen_at")
            or incident.get("first_seen_at")
            or 0
        )

        if last_seen and now - last_seen > 1800:
            continue

        source_task_id = str(
            incident.get("task_id") or ""
        )

        if not source_task_id:
            continue

        if _queue_control_continue(
            state,
            source_task_id,
            "CHAT_ACK_STALL_FALLBACK",
        ):
            changed = True

    return changed


def _next_control_continue_item(
    state: dict,
    ai_acked: set[str],
) -> dict | None:
    for item in state.get(
        "control_continue_queue",
        [],
    ):
        task_id = str(item.get("task_id") or "")

        if not task_id or task_id in ai_acked:
            continue

        return item

    return None
'''

TEST_CONTENT = r'''
from pathlib import Path
import importlib
import json
import sys


def load_bridge():
    root = Path(__file__).resolve().parents[2]
    control = root / "control"

    if str(control) not in sys.path:
        sys.path.insert(0, str(control))

    return importlib.import_module("browser_bridge")


def write_result(results, task_id, status="completed"):
    result_dir = results / task_id
    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / "RESULT.json").write_text(
        json.dumps(
            {
                "task_id": task_id,
                "status": status,
                "task_class": "infrastructure",
                "hypothesis_id": "CONTROL-AUTO-CONTINUE",
                "exit_code": 0 if status == "completed" else 1,
                "source_commit": "abc123",
            }
        ),
        encoding="utf-8",
    )


def test_ack_queues_control_continue(tmp_path, monkeypatch):
    bb = load_bridge()

    state_file = tmp_path / "bridge_state.json"
    results = tmp_path / "results"
    task_id = "CONTROL-AUTO-CONTINUE-TEST-001"

    write_result(results, task_id)

    state_file.write_text(
        json.dumps(
            {
                "bridge_tasks": [task_id],
                "acked": [],
                "ai_acked": [],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(bb, "STATE_FILE", state_file)
    monkeypatch.setattr(bb, "RESULTS", results)
    monkeypatch.setattr(
        bb,
        "lifecycle_update",
        lambda *args, **kwargs: None,
    )

    ack = bb.acknowledge(task_id)

    assert ack["ok"] is True

    state = bb.load_state()
    assert state["control_continue_seen"] == [task_id]

    item = bb.next_ai_outbox_item()

    assert item["kind"] == "AI_WORK_BUNDLE"
    assert item["schema"] == "PVA_CONTROL_CONTINUE_V1"
    assert item["bundle"]["source_task_id"] == task_id
    assert item["guardrails"]["direct_executor_route"] is False


def test_ai_ack_consumes_control_continue(tmp_path, monkeypatch):
    bb = load_bridge()

    state_file = tmp_path / "bridge_state.json"
    results = tmp_path / "results"
    task_id = "CONTROL-AUTO-CONTINUE-TEST-002"

    write_result(results, task_id)

    item = bb._control_continue_item(
        task_id,
        "RESULT_ACKED",
    )

    state_file.write_text(
        json.dumps(
            {
                "bridge_tasks": [task_id],
                "acked": [task_id],
                "ai_acked": [],
                "control_continue_seen": [task_id],
                "control_continue_queue": [item],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(bb, "STATE_FILE", state_file)
    monkeypatch.setattr(bb, "RESULTS", results)

    offered = bb.next_ai_outbox_item()
    assert offered["task_id"] == item["task_id"]

    ack = bb.acknowledge_ai(item["task_id"])
    assert ack["ok"] is True

    state = bb.load_state()
    assert item["task_id"] in state["ai_acked"]

    assert bb.next_ai_outbox_item() is None
'''


def run(*args: str):
    return subprocess.run(
        list(args),
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


original_bridge = BRIDGE.read_text(encoding="utf-8")
original_test = (
    TEST.read_text(encoding="utf-8")
    if TEST.exists()
    else None
)

text = original_bridge

if "def _control_continue_result(" not in text:
    anchor = "\ndef next_ai_outbox_item() -> dict | None:\n"
    if anchor not in text:
        raise RuntimeError("next_ai_outbox_item anchor missing")
    text = text.replace(
        anchor,
        "\n" + HELPERS.strip() + "\n\n" + anchor.lstrip("\n"),
        1,
    )

next_ai_start = text.index("def next_ai_outbox_item() -> dict | None:")
next_ai_end = text.index("\ndef acknowledge_ai(", next_ai_start)
next_ai_block = text[next_ai_start:next_ai_end]

if "_next_control_continue_item(" not in next_ai_block:
    needle = (
        "def next_ai_outbox_item() -> dict | None:\n"
        "    state = load_state()\n"
        "    ai_acked = set(state.get(\"ai_acked\", []))\n"
    )
    insert = (
        needle
        + "\n"
        + "    if _sync_recent_ack_stall_fallbacks(state):\n"
        + "        save_state(state)\n\n"
        + "    control_item = _next_control_continue_item(\n"
        + "        state,\n"
        + "        ai_acked,\n"
        + "    )\n\n"
        + "    if control_item is not None:\n"
        + "        return control_item\n"
    )
    if needle not in text:
        raise RuntimeError("next_ai_outbox state anchor missing")
    text = text.replace(needle, insert, 1)

ack_start = text.index("def acknowledge(task_id: str) -> dict:")
ack_end = text.index("\n\nclass Handler", ack_start)
ack_block = text[ack_start:ack_end]

if "_queue_control_continue(" not in ack_block:
    save_anchor = "    save_state(state)\n"
    replacement = (
        "    _queue_control_continue(\n"
        "        state,\n"
        "        task_id,\n"
        "        \"RESULT_ACKED\",\n"
        "    )\n\n"
        "    save_state(state)\n"
    )
    if save_anchor not in ack_block:
        raise RuntimeError("ack save_state anchor missing")
    ack_block = ack_block.replace(
        save_anchor,
        replacement,
        1,
    )
    text = text[:ack_start] + ack_block + text[ack_end:]

BRIDGE.write_text(text, encoding="utf-8")
TEST.parent.mkdir(parents=True, exist_ok=True)
TEST.write_text(TEST_CONTENT.strip() + "\n", encoding="utf-8")

compile_result = run(
    sys.executable,
    "-m",
    "py_compile",
    "control/browser_bridge.py",
)

pytest_result = None

if compile_result.returncode == 0:
    pytest_result = run(
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "tests/bridge/test_control_auto_continue.py",
    )

ok = (
    compile_result.returncode == 0
    and pytest_result is not None
    and pytest_result.returncode == 0
)

print(compile_result.stdout)
print(compile_result.stderr)

if pytest_result is not None:
    print(pytest_result.stdout)
    print(pytest_result.stderr)

if not ok:
    BRIDGE.write_text(
        original_bridge,
        encoding="utf-8",
    )

    if original_test is None:
        TEST.unlink(missing_ok=True)
    else:
        TEST.write_text(
            original_test,
            encoding="utf-8",
        )

    raise SystemExit("AUTO_CONTINUE_TEST_FAILED")

if LEDGER.exists():
    ledger = LEDGER.read_text(encoding="utf-8")
    marker = "## 2026-09-21 — E020R CONTROL_AUTO_CONTINUE"

    if marker not in ledger:
        ledger = ledger.rstrip() + "\n\n" + marker + "\n\n" + (
            "- Laag: control-plane continuation / AI outbox.\n"
            "- Probleem: na een geldig bridge-resultaat kon de assistant "
            "een statusantwoord geven zonder een volgende lokale taak, "
            "waardoor de keten stilviel tot handmatig `ga door`.\n"
            "- Fix: `acknowledge()` queue't nu een durable control-continuation "
            "AI-work item; `/ai-outbox` geeft dit automatisch terug aan ChatGPT.\n"
            "- Fallback: recente `CHAT_ACK_STALL` incidents mogen dezelfde "
            "continuation queue vullen wanneer normale result-ACK ontbreekt.\n"
            "- Dedupe: elk source task-id wordt maximaal eenmaal als "
            "continuation-bron gequeued; AI ack voorkomt herlevering.\n"
            "- Guardrails: geen direct executor-pad, live trading, paid actions, "
            "wallet actions of OpenAI API.\n"
            "- Tests: py_compile + dedicated pytest moeten PASS zijn voor commit.\n"
            "- Prospectieve gate: E020R moet na zijn eigen result automatisch "
            "een nieuwe AI continuation user-turn veroorzaken.\n"
        )
        LEDGER.write_text(
            ledger,
            encoding="utf-8",
        )

subprocess.run(
    [
        "git",
        "add",
        "control/browser_bridge.py",
        "tests/bridge/test_control_auto_continue.py",
        "control/BRIDGE_INCIDENT_LEDGER.md",
    ],
    cwd=ROOT,
    check=True,
)

staged = subprocess.run(
    ["git", "diff", "--cached", "--quiet"],
    cwd=ROOT,
)

if staged.returncode != 0:
    subprocess.run(
        [
            "git",
            "commit",
            "-m",
            "fix: auto continue control plane after bridge results",
        ],
        cwd=ROOT,
        check=True,
    )

restart = run(
    "systemctl",
    "--user",
    "restart",
    "prediction-research-browser-bridge.service",
)

if restart.returncode != 0:
    raise SystemExit(
        "BRIDGE_RESTART_FAILED: " + restart.stderr.strip()
    )

time.sleep(2)

with urllib.request.urlopen(
    "http://127.0.0.1:8765/health",
    timeout=5,
) as response:
    body = response.read().decode()
    if response.status != 200:
        raise SystemExit(
            "BRIDGE_HEALTH_FAILED: " + body
        )

print("AUTO_CONTINUE_PATCH=PASS")
print("PY_COMPILE=PASS")
print("PYTEST=PASS")
print("BRIDGE_RESTART=PASS")
print("HEALTH_200=PASS")
print(
    "HEAD="
    + run("git", "rev-parse", "HEAD").stdout.strip()
)
