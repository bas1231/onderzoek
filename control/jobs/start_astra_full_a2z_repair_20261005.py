from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BRIDGE = Path.home() / ".local" / "share" / "prediction-chat-bridge"
ROUTE_CONFIG = BRIDGE / "autobuild_control_route.json"
ROUTES = BRIDGE / "routes"
CID = "AUTO-DISCOVERY-54d13314c7879b58e46d"


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return value


def load_continuation():
    path = ROOT / "control" / "tampermonkey_multichat" / "continuation_manager.py"
    spec = importlib.util.spec_from_file_location("prediction_astra_full_a2z_cont", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("continuation_manager unavailable")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    config = load_json(ROUTE_CONFIG)
    route_task_id = str(config.get("route_task_id") or "").strip()
    if not route_task_id:
        raise RuntimeError("ASTRA route task missing")
    route = load_json(ROUTES / f"{route_task_id}.json")
    chat_id = str(route.get("chat_id") or "").strip()
    if not chat_id:
        raise RuntimeError("ASTRA chat route missing")

    source_task_id = "ASTRA-FULL-A2Z-REPAIR-20261005-V1"
    context = """PREDICTION_ASTRA_FULL_A2Z_REPAIR_V1
required_model=GPT-6 Astra
candidate_id=AUTO-DISCOVERY-54d13314c7879b58e46d
qualification_id=FULL-A2Z-LIVE-20261004-V4
objective=Execute the complete Prediction A-to-Z qualification, diagnose the first real failure, repair it narrowly, add regression coverage where appropriate, and rerun until the complete governed chain is green or a genuine hard blocker remains.

You are the supervising test-and-repair agent for this qualification campaign. If you are not actually GPT-6 Astra, choose BLOCKED and do not author changes.

Before changing anything, read the current canonical Prediction source of truth:
00_CHATGPT_START_HERE.md
control/bridge_commands/CURRENT_STATE.md
control/bridge_commands/SESSION_ROUTING.md
control/NEW_SESSION_LOCAL_EXECUTION.md
control/PROJECT_EXECUTOR.md
control/bridge_commands/OPERATIONS.md
control/tampermonkey_multichat/PROTOCOL.md
control/tampermonkey_multichat/CHATGPT_PROJECT_INSTRUCTIONS.md
methodology/EDGE_DISCOVERY_MODEL_GATES.md

Use the existing GitHub command bus and capability-scoped projectexecutor. Do not ask the human to paste terminal commands. Inspect the current V4 qualification candidate/evidence and existing runtime evidence first. Reproduce each failure before fixing it. Distinguish test-harness mistakes from real system failures. For a real failure, determine the first incomplete stage, apply the smallest bounded repair, add or strengthen a regression test where useful, run targeted tests, then rerun the full A-to-Z qualification.

The intended governed chain is:
synthetic primary-scout intake validation -> durable candidate -> queue -> real Director reasoning -> Astra PREBUILD gate -> governed build using the project's required builder policy -> technical positive/negative controls -> Director -> Astra PREMEASUREMENT gate -> read-only/shadow qualification measurement -> final Director -> final report.
Preserve the production model gates rather than bypassing or faking them. Synthetic qualification observations never count as economic evidence. Scientific status remains NO_PROVEN_EDGE unless the formal economic proof gates are genuinely met.

Authorization for this campaign includes ordinary bounded repository edits, tests, isolated worktrees/local commits, allowlisted Prediction runtime installs, and prediction-* user-service diagnosis/restart only when necessary to validate a repair. Do not broaden scope beyond the first demonstrated failure.

Hard boundaries remain absolute:
live_trading=false
paid_actions=false
wallet_actions=false
order_submission=false
remote_git_push=false
credential_access=false
sudo_or_root=false
unrestricted_external_network=false

Use immutable task IDs. Require status=PASS exit=0 plus task-specific assertions before calling a stage green. On failure diagnose and retry with a fresh task ID. When the complete A-to-Z chain is proven, create durable final qualification evidence/report in canonical Git and choose DONE. If a genuine unavailable capability, login/KYC, specific paid action, trade/wallet approval, or unreachable command bus is essential, choose BLOCKED with the exact blocker.
"""
    continuation = load_continuation()
    record = continuation.start_external_continuation(
        data_dir=BRIDGE,
        source_task_id=source_task_id,
        chat_id=chat_id,
        expected_route_task_id=route_task_id,
        context_message=context,
        source_kind="ASTRA_FULL_A2Z_REPAIR",
    )
    print(json.dumps({
        "status": "PASS",
        "required_model": "GPT-6 Astra",
        "source_task_id": source_task_id,
        "continuation_id": record.get("continuation_id"),
        "continuation_state": record.get("state"),
        "route_task_id": route_task_id,
        "candidate_id": CID,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
