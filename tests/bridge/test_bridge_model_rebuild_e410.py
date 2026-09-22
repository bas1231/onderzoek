from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_core_has_explicit_bridge_envelope_rebuild():
    src = (
        ROOT / "control/browser_bridge_core.py"
    ).read_text(encoding="utf-8")

    assert "BridgeEnvelope.model_rebuild(" in src
    assert '"FileWrite": FileWrite' in src
    assert '"Task": Task' in src


def test_real_wrapper_can_validate_bridge_envelope():
    code = r"""
import importlib.util
import sys
from pathlib import Path

root = Path.cwd()
control = root / "control"

sys.path.insert(0, str(control))

path = control / "browser_bridge.py"

spec = importlib.util.spec_from_file_location(
    "e410_browser_bridge_wrapper",
    path,
)

mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

payload = {
    "bridge_version": 1,
    "commit_message": "control: E410 wrapper validation",
    "files": [],
    "task": {
        "task_id": "CONTROL-E410-MODEL-VALIDATION",
        "hypothesis_id": "CONTROL-BRIDGE-E410",
        "task_class": "infrastructure",
        "operation": "health_check",
        "working_directory": ".",
        "command": [
            ".venv/bin/python",
            "experiments/health_check.py",
        ],
        "timeout_seconds": 60,
        "live_trading": False,
        "build_authorization": {
            "mode": "control_plane",
            "build_kind": "control_plane",
            "objective": "Validate wrapper model resolution",
            "capabilities": [
                "read_repository",
            ],
        },
    },
}

obj = mod.BridgeEnvelope.model_validate(payload)

assert obj.task.task_id == "CONTROL-E410-MODEL-VALIDATION"
assert obj.files == []

print("WRAPPER_MODEL_VALIDATE_PASS")
"""

    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 0, (
        "stdout:\\n"
        + proc.stdout
        + "\\nstderr:\\n"
        + proc.stderr
    )

    assert (
        "WRAPPER_MODEL_VALIDATE_PASS"
        in proc.stdout
    )
