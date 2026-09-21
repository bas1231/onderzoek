#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PYTHON = Path(sys.executable)

TARGET_TESTS = [
    "tests/hourly/test_ai_bridge_outbox.py",
    "tests/hourly/test_ai_handoff.py",
    "tests/hourly/test_ai_response.py",
    "tests/hourly/test_ai_response_receiver.py",
    "tests/hourly/test_ai_transport.py",
    "tests/hourly/test_ai_result_state_preservation_v13.py",
    "tests/hourly/test_specialist_worker_wiring_v13.py",
    "tests/hourly/test_worker_role_contract_v13.py",
    "tests/hourly/test_agent_orchestrator.py",
    "tests/hourly/test_packet_hydrator.py",
    "tests/bridge/test_ai_response_endpoint_v13.py",
    "tests/test_recon_engine.py",
]


def run(args: list[str], timeout: int = 180) -> dict:
    proc = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout[-12000:],
        "stderr": proc.stderr[-12000:],
        "status": "PASS" if proc.returncode == 0 else "FAIL",
    }


def main() -> int:
    steps: dict[str, dict] = {}

    steps["target_tests"] = run(
        [str(PYTHON), "-m", "pytest", "-q", *TARGET_TESTS],
        timeout=240,
    )

    steps["python_compile"] = run(
        [
            str(PYTHON),
            "-m",
            "compileall",
            "-q",
            "control",
            "tests/hourly",
            "tests/bridge",
            "tests/test_recon_engine.py",
        ],
        timeout=180,
    )

    steps["hourly_bridge_regression"] = run(
        [
            str(PYTHON),
            "-m",
            "pytest",
            "-q",
            "tests/hourly",
            "tests/bridge",
            "tests/test_recon_engine.py",
        ],
        timeout=300,
    )

    node = shutil.which("node")
    if node:
        steps["javascript_syntax"] = run(
            [
                node,
                "--check",
                "control/browser_extension/ai_response_capture.js",
            ],
            timeout=60,
        )
        for name in ("background.js", "content.js"):
            check = run(
                [node, "--check", f"control/browser_extension/{name}"],
                timeout=60,
            )
            if check["returncode"] != 0:
                steps["javascript_syntax"] = check
                break
    else:
        steps["javascript_syntax"] = {
            "status": "SKIP_NODE_NOT_INSTALLED",
            "returncode": None,
            "stdout": "",
            "stderr": "",
        }

    required = [
        steps["target_tests"],
        steps["python_compile"],
        steps["hourly_bridge_regression"],
    ]
    if node:
        required.append(steps["javascript_syntax"])

    ok = all(step.get("status") == "PASS" for step in required)

    head = run(["git", "rev-parse", "HEAD"], timeout=30)
    branch = run(["git", "branch", "--show-current"], timeout=30)
    diff = run(["git", "status", "--short"], timeout=30)

    payload = {
        "task": "READY-SPECIALIST-WORKER-V13-VALIDATION",
        "status": "PASS" if ok else "BLOCKED_TEST_FAILURE",
        "branch": branch.get("stdout", "").strip(),
        "head": head.get("stdout", "").strip(),
        "working_tree_status": diff.get("stdout", ""),
        "steps": steps,
        "economic_conclusion": "NO_PROVEN_EDGE",
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "openai_api": False,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
