from pathlib import Path
import subprocess
import sys

ROOT = Path.cwd()
TARGET = ROOT / "control/jobs/install_control_auto_continue_e020r.py"

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
        "origin/main:control/jobs/install_control_auto_continue_e020r.py",
    ],
    cwd=ROOT,
    text=True,
    capture_output=True,
)
if show.returncode != 0:
    print(show.stderr, file=sys.stderr)
    raise SystemExit(show.returncode)

text = show.stdout

needle = '''    write_result(results, task_id)

    item = bb._control_continue_item(
        task_id,
        "RESULT_ACKED",
    )
'''
replacement = '''    write_result(results, task_id)

    # _control_continue_item reads bb.RESULTS immediately, so the
    # isolated tmp results directory must be active before item creation.
    monkeypatch.setattr(bb, "RESULTS", results)

    item = bb._control_continue_item(
        task_id,
        "RESULT_ACKED",
    )
'''

if needle not in text:
    raise SystemExit("AUTO_CONTINUE_TEST_PATCH_ANCHOR_MISSING")

text = text.replace(needle, replacement, 1)

# A fallback wake must not replay a whole recent incident backlog.
# Only the newest ACK stall is eligible per bridge state generation.
text = text.replace(
    ''')[:20]\n\n    for incident_path in incident_paths:''',
    ''')[:1]\n\n    for incident_path in incident_paths:''',
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
    raise SystemExit("INSTALLER_PY_COMPILE_FAILED")

run = subprocess.run(
    [sys.executable, str(TARGET)],
    cwd=ROOT,
    text=True,
)

raise SystemExit(run.returncode)
