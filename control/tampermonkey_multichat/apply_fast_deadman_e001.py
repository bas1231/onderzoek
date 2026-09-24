#!/usr/bin/env python3
"""Apply the E001 fast dead-man bridge hotfix idempotently.

Scope is intentionally narrow:
- preserve normal RESULT_READY delivery and task dedupe;
- reduce the server fallback from 10 minutes to 15 seconds;
- force old persisted 600s modes to an effective 15s interval;
- include a unique continuation nonce and require a fresh task_id on retry;
- align heartbeat CLI defaults with the 15s fallback;
- add focused offline regression coverage.
"""
from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
SERVER = HERE / "bridge_server_hardened.py"
HEARTBEAT = HERE / "nightshift_server_heartbeat.py"
TEST = HERE / "test_bridge_fast_deadman.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one old fragment, found {count}")
    return text.replace(old, new, 1)


def patch_server() -> None:
    text = SERVER.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "Only ten full minutes without either kind of activity produce a wake message.",
        "Only fifteen seconds without either kind of activity produce a dead-man wake message.",
        "server doc interval",
    )
    text = replace_once(
        text,
        "DEFAULT_HEARTBEAT_INTERVAL = 600.0\nHEARTBEAT_MESSAGE = (\n    \"ga door. Als de afgesproken nightshift-taak volledig is afgerond, \"\n    \"negeer deze heartbeat en start niets nieuws.\"\n)\n",
        "DEFAULT_HEARTBEAT_INTERVAL = 15.0\n\n\ndef heartbeat_message(token: str) -> str:\n    return (\n        \"ga door. Als de afgesproken taak volledig is afgerond, negeer deze heartbeat \"\n        \"en start niets nieuws. Als een nieuwe WSL-uitvoering nodig is: gebruik ALTIJD \"\n        \"een NIEUWE task_id/execution-id; herhaal nooit een eerder gebruikte task_id. \"\n        f\"Continuation nonce: {token}.\"\n    )\n",
        "server heartbeat message",
    )
    text = replace_once(
        text,
        "    return min(600.0, max(15.0, value))\n",
        "    # Dead-man fallback must never reintroduce the historical 10-minute stall.\n    return min(DEFAULT_HEARTBEAT_INTERVAL, max(15.0, value))\n",
        "server effective interval",
    )
    text = replace_once(
        text,
        '            "message": HEARTBEAT_MESSAGE,\n',
        '            "message": heartbeat_message(token),\n',
        "server event message",
    )
    text = replace_once(
        text,
        '                "heartbeat_resets_on_assistant_command": True,\n',
        '                "heartbeat_resets_on_assistant_command": True,\n                "heartbeat_retry_nonce": True,\n                "heartbeat_fresh_task_id_required": True,\n',
        "server health flags",
    )
    SERVER.write_text(text, encoding="utf-8")


def patch_heartbeat_cli() -> None:
    text = HEARTBEAT.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '    p_enable.add_argument("--interval", type=float, default=600.0)\n    p_enable.add_argument("--delay", type=float, default=600.0)\n',
        '    p_enable.add_argument("--interval", type=float, default=15.0)\n    p_enable.add_argument("--delay", type=float, default=15.0)\n',
        "heartbeat CLI defaults",
    )
    HEARTBEAT.write_text(text, encoding="utf-8")


def write_test() -> None:
    TEST.write_text(
        '''#!/usr/bin/env python3\nfrom __future__ import annotations\n\nimport importlib\nimport sys\nimport unittest\nfrom pathlib import Path\n\nHERE = Path(__file__).resolve().parent\nif str(HERE) not in sys.path:\n    sys.path.insert(0, str(HERE))\n\nh = importlib.import_module("bridge_server_hardened")\n\n\nclass FastDeadmanBridgeTests(unittest.TestCase):\n    def test_deadman_interval_is_15_seconds_even_for_legacy_mode(self):\n        self.assertEqual(h.DEFAULT_HEARTBEAT_INTERVAL, 15.0)\n        self.assertEqual(h._heartbeat_interval({"interval_seconds": 600.0}), 15.0)\n        self.assertEqual(h._heartbeat_interval({}), 15.0)\n\n    def test_retry_message_requires_fresh_execution_id_and_nonce(self):\n        msg = h.heartbeat_message("cafebabe")\n        self.assertIn("cafebabe", msg)\n        self.assertIn("NIEUWE task_id", msg)\n        self.assertIn("herhaal nooit", msg)\n\n    def test_cli_defaults_are_fast(self):\n        source = (HERE / "nightshift_server_heartbeat.py").read_text(encoding="utf-8")\n        self.assertIn('p_enable.add_argument("--interval", type=float, default=15.0)', source)\n        self.assertIn('p_enable.add_argument("--delay", type=float, default=15.0)', source)\n\n\nif __name__ == "__main__":\n    unittest.main()\n''',
        encoding="utf-8",
    )


def main() -> int:
    patch_server()
    patch_heartbeat_cli()
    write_test()
    print("FAST_DEADMAN_PATCH=APPLIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
