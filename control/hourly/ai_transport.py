from __future__ import annotations

from pathlib import Path
from typing import Any
import json


ROOT = Path.cwd()
RUNS = ROOT / "knowledge/runs"

WAKE_REASON = "HOURLY_RESEARCH_WAKE"
SCHEMA = "PVA_AI_CHAT_WORK_V1"
AI_RESPONSE_START = "<<<PREDICTION_AI_RESPONSE>>>"
AI_RESPONSE_END = "<<<END_PREDICTION_AI_RESPONSE>>>"


class TransportError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise TransportError(message)


def safe_run_id(value: Any) -> str:
    run_id = str(value or "")
    require(run_id.startswith("hourly-"), "invalid run_id")
    require("/" not in run_id, "unsafe run_id")
    require("\\" not in run_id, "unsafe run_id")
    require(".." not in run_id, "unsafe run_id")
    require(len(run_id) <= 160, "run_id too long")
    return run_id


def run_id_from_incident(incident: dict[str, Any]) -> str:
    require(
        incident.get("reason") == WAKE_REASON,
        "not an hourly research wake",
    )

    task_id = str(incident.get("task_id") or "")

    prefix = "hourly-research-"
    require(task_id.startswith(prefix), "invalid hourly wake task_id")

    stamp = task_id[len(prefix):]
    require(bool(stamp), "missing hourly wake timestamp")

    # Wake IDs:
    # hourly-research-20260920T1700+0200
    #
    # Run IDs:
    # hourly-20260920T170000+0200
    #
    # Convert only this known format. Do not guess arbitrary IDs.
    if len(stamp) >= 13 and "T" in stamp:
        date_part, time_part = stamp.split("T", 1)

        sign_pos = max(
            time_part.find("+"),
            time_part.find("-"),
        )

        if sign_pos > 0:
            hhmm = time_part[:sign_pos]
            offset = time_part[sign_pos:]
        else:
            hhmm = time_part
            offset = ""

        require(
            len(date_part) == 8
            and date_part.isdigit(),
            "invalid wake date",
        )
        require(
            len(hhmm) == 4
            and hhmm.isdigit(),
            "invalid wake time",
        )

        run_id = (
            "hourly-"
            + date_part
            + "T"
            + hhmm
            + "00"
            + offset
        )
        return safe_run_id(run_id)

    raise TransportError("unsupported hourly wake id")


def bundle_path(run_id: str) -> Path:
    run_id = safe_run_id(run_id)
    return RUNS / f"{run_id}-ai-work-bundle.json"


def response_path(run_id: str) -> Path:
    run_id = safe_run_id(run_id)
    return RUNS / f"{run_id}-ai-response.json"


def receipt_path(run_id: str) -> Path:
    run_id = safe_run_id(run_id)
    return RUNS / f"{run_id}-ai-response-receipt.json"


def build_chat_item(
    incident: dict[str, Any],
    *,
    run_id: str | None = None,
) -> dict[str, Any]:

    require(
        incident.get("deliver_to_chat") is True,
        "incident not marked for chat delivery",
    )
    require(
        incident.get("status") == "OPEN",
        "incident not open",
    )
    require(
        incident.get("reason") == WAKE_REASON,
        "incident is not hourly research wake",
    )

    resolved_run_id = safe_run_id(
        run_id or run_id_from_incident(incident)
    )

    bundle = bundle_path(resolved_run_id)

    require(bundle.exists(), "AI work bundle missing")

    data = json.loads(bundle.read_text(encoding="utf-8"))

    require(
        data.get("schema") == "PVA_AI_WORK_BUNDLE_V1",
        "unexpected bundle schema",
    )
    require(
        data.get("run_id") == resolved_run_id,
        "bundle run_id mismatch",
    )
    delivery_policy = data.get("delivery_policy") or {}

    require(
        delivery_policy.get("single_chatgpt_turn") is True,
        "bundle is not single-turn",
    )

    guardrails = data.get("guardrails") or {}

    require(
        guardrails.get("live_trading") is False,
        "live trading guardrail missing",
    )
    require(
        guardrails.get("paid_actions") is False,
        "paid action guardrail missing",
    )
    require(
        guardrails.get("wallet_actions") is False,
        "wallet action guardrail missing",
    )
    require(
        guardrails.get("openai_api") is False,
        "OpenAI API guardrail missing",
    )

    # Important:
    # This is deliberately NOT a BridgeEnvelope and contains no
    # command/shell/argv/executable field. It can never be sent to
    # executor.py as a normal bridge task.
    return {
        "kind": "AI_WORK_BUNDLE",
        "schema": SCHEMA,
        "task_id": str(incident["task_id"]),
        "run_id": resolved_run_id,
        "bundle_ref": str(bundle.relative_to(ROOT)),
        "bundle": data,
        "response_contract": {
            "schema": "PVA_AI_RESPONSE_V1",
            "response_ref": str(
                response_path(resolved_run_id).relative_to(ROOT)
            ),
            "validator": "control/hourly/ai_response.py",
            "marker_start": AI_RESPONSE_START,
            "marker_end": AI_RESPONSE_END,
            "economic_conclusion": "NO_PROVEN_EDGE",
            "direct_execution_allowed": False,
        },
        "instruction": (
            "Act as the Prediction Research Director for this single "
            "hourly run. Analyze the bundled specialist work and candidate "
            "handoff in one ChatGPT turn. Return exactly one structured "
            "PVA_AI_RESPONSE_V1 JSON object, wrapped between the literal "
            f"markers {AI_RESPONSE_START} and {AI_RESPONSE_END}. Do not put "
            "prose, Markdown fences, or any other content inside or outside "
            "that marker block. Preserve NO_PROVEN_EDGE unless later "
            "separately validated gates permit otherwise; this transport "
            "itself never authorizes promotion. Recon WATCH triage is "
            "research-only and has no promotion authority. Do not return "
            "executable shell, argv or commands. Local work may only be "
            "requested descriptively through local_task_spec. No live "
            "trading, paid actions, wallet actions or OpenAI API."
        ),
        "guardrails": {
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "openai_api": False,
            "direct_executor_route": False,
        },
    }


def should_offer_ai_work(
    incident: dict[str, Any],
    *,
    run_id: str | None = None,
) -> bool:
    try:
        resolved = safe_run_id(
            run_id or run_id_from_incident(incident)
        )

        if response_path(resolved).exists():
            return False

        if receipt_path(resolved).exists():
            return False

        build_chat_item(
            incident,
            run_id=resolved,
        )

        return True

    except (TransportError, OSError, json.JSONDecodeError):
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--incident", required=True)
    parser.add_argument("--run-id")
    args = parser.parse_args()

    incident = json.loads(
        Path(args.incident).read_text(encoding="utf-8")
    )

    item = build_chat_item(
        incident,
        run_id=args.run_id,
    )

    print(json.dumps(item, indent=2, sort_keys=True))
