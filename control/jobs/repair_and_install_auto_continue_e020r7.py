from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path.cwd()
TARGET = ROOT / "control/jobs/install_control_auto_continue_e020r7.py"

fetch = subprocess.run(
    ["git", "fetch", "origin", "main"],
    cwd=ROOT,
    text=True,
    capture_output=True,
)
if fetch.returncode != 0:
    print(fetch.stderr, file=sys.stderr)
    raise SystemExit(fetch.returncode)

show = subprocess.run(
    [
        "git",
        "show",
        "origin/main:control/jobs/install_control_auto_continue_e020r6.py",
    ],
    cwd=ROOT,
    text=True,
    capture_output=True,
)
if show.returncode != 0:
    print(show.stderr, file=sys.stderr)
    raise SystemExit(show.returncode)

text = show.stdout

old = '''    ai_ack = bb.acknowledge_ai(offered["task_id"])
    assert ai_ack["ok"] is True
    assert offered["task_id"] in bb.load_state()["ai_acked"]
    assert bb.next_ai_outbox_item() is None
'''

new = '''    ai_ack = bb.acknowledge_ai(offered["task_id"])
    assert ai_ack["ok"] is True

    state = bb.load_state()
    assert offered["task_id"] in state["ai_acked"]

    # Other legitimate AI work (for example an hourly research wake)
    # may already be pending in the real incident directory. The invariant
    # under test is only that this control-continuation item is consumed.
    assert bb._next_control_continue_item(
        state,
        set(state.get("ai_acked", [])),
    ) is None
'''

if old not in text:
    raise SystemExit("AUTO_CONTINUE_R7_TEST_ANCHOR_MISSING")

text = text.replace(old, new, 1)
text = text.replace(
    "## 2026-09-21 — E020R6 CONTROL_AUTO_CONTINUE",
    "## 2026-09-21 — E020R7 CONTROL_AUTO_CONTINUE",
    1,
)
text = text.replace(
    "fix: install durable control auto continuation",
    "fix: install durable control auto continuation r7",
    1,
)

TARGET.write_text(text, encoding="utf-8")

compile_installer = subprocess.run(
    [sys.executable, "-m", "py_compile", str(TARGET)],
    cwd=ROOT,
    text=True,
    capture_output=True,
)
if compile_installer.returncode != 0:
    print(compile_installer.stdout)
    print(compile_installer.stderr, file=sys.stderr)
    raise SystemExit("R7_INSTALLER_PY_COMPILE_FAILED")

run = subprocess.run(
    [sys.executable, str(TARGET)],
    cwd=ROOT,
    text=True,
)
raise SystemExit(run.returncode)
