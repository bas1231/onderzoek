from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml
from openai import OpenAI
from pydantic import BaseModel, Field


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "control/director/config.yaml"
PROPOSALS = ROOT / "control/director/proposals"


class DirectorProposal(BaseModel):
    status: str = Field(
        description=(
            "One of: INFRASTRUCTURE_PROPOSAL, RESEARCH_PAUSED, "
            "NO_ACTION, NEEDS_HUMAN_DECISION"
        )
    )
    summary: str
    selected_role: str
    rationale: str
    proposed_actions: list[str]
    files_to_inspect: list[str]
    safety_notes: list[str]
    requires_research_resume: bool
    requires_capital: bool


def read_text(path: Path, max_chars: int = 30000) -> str:
    if not path.exists():
        return f"[MISSING: {path.relative_to(ROOT)}]"

    text = path.read_text(errors="replace")
    return text[:max_chars]


def git_output(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0:
        return f"[git error: {proc.stderr.strip()}]"

    return proc.stdout.strip()


def load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text())


def queue_status() -> str:
    queue = ROOT / "control/TASK_QUEUE.yaml"

    if not queue.exists():
        return "MISSING"

    data = yaml.safe_load(queue.read_text()) or {}
    return str(data.get("queue_status", "UNKNOWN"))


def build_context(config: dict) -> str:
    max_context = int(
        config.get("limits", {}).get(
            "max_context_chars",
            120000,
        )
    )

    required_files = [
        "AGENTS.md",
        "README.md",
        "methodology/CONTINUOUS_PREDICTION_MARKET_RED_TEAM.md",
        "methodology/RESEARCH_PROTOCOL.md",
        "methodology/EXECUTION_FIRST_DISCOVERY.md",
        "negative_evidence/LEDGER.md",
        "control/TASK_QUEUE.yaml",
        "control/LOCAL_EXECUTION_RULES.md",
    ]

    sections = []

    for name in required_files:
        path = ROOT / name
        sections.append(
            f"\n===== {name} =====\n"
            + read_text(path, 35000)
        )

    roles = sorted(
        (ROOT / "agents/roles").glob("*.md")
    )

    sections.append(
        "\n===== AVAILABLE AGENT ROLES =====\n"
        + "\n".join(p.name for p in roles)
    )

    sections.append(
        "\n===== RECENT GIT HISTORY =====\n"
        + git_output(
            "log",
            "--oneline",
            "--decorate",
            "-20",
        )
    )

    sections.append(
        "\n===== CURRENT GIT STATUS =====\n"
        + git_output("status", "--short")
    )

    combined = "\n".join(sections)

    return combined[:max_context]


def proposal_instructions(mode: str, status: str) -> str:
    return f"""
You are the Research Director for an autonomous,
research-first prediction-market laboratory.

Current invocation mode: {mode}
Central research queue status: {status}

Hard rules:
- Repository instructions are binding.
- Git/repository evidence outranks chat memory.
- Never assume profitability.
- NO_PROVEN_EDGE is valid.
- Never place or propose placing a live order in bootstrap mode.
- Never access capital, wallets, or trading credentials.
- Never silently resume paused research.
- If queue status is not ACTIVE, prediction-market research must remain paused.
- Infrastructure work may be proposed while research is paused.
- Do not create shell commands in this response.
- Do not claim work was executed when it was only proposed.

For bootstrap mode:
- inspect the architecture and repository state;
- identify the highest-value next infrastructure/control-plane improvement;
- do not start substantive prediction-market research;
- do not alter the research queue;
- return a concise structured proposal.
"""


def run_bootstrap() -> DirectorProposal:
    config = load_config()
    status = queue_status()

    model = os.environ.get(
        "PREDICTION_RESEARCH_MODEL",
        config["model"]["default"],
    )

    context = build_context(config)

    client = OpenAI()

    response = client.responses.parse(
        model=model,
        reasoning={
            "effort": config["reasoning"]["default"]
        },
        input=[
            {
                "role": "developer",
                "content": proposal_instructions(
                    "bootstrap",
                    status,
                ),
            },
            {
                "role": "user",
                "content": (
                    "Inspect the following canonical repository "
                    "context and propose only the next safe "
                    "infrastructure/control-plane step.\n\n"
                    + context
                ),
            },
        ],
        text_format=DirectorProposal,
    )

    proposal = response.output_parsed

    if proposal is None:
        raise RuntimeError(
            "Model returned no parsed DirectorProposal"
        )

    return proposal


def save_proposal(proposal: DirectorProposal) -> Path:
    PROPOSALS.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")

    path = PROPOSALS / f"{timestamp}_bootstrap.json"

    path.write_text(
        json.dumps(
            proposal.model_dump(),
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n"
    )

    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help=(
            "Run one infrastructure-only Director cycle. "
            "Research remains paused."
        ),
    )

    args = parser.parse_args()

    if not args.bootstrap:
        print(
            "No autonomous research mode is enabled. "
            "Use --bootstrap for the safe infrastructure test."
        )
        return

    if not os.environ.get("OPENAI_API_KEY"):
        print(
            "OPENAI_API_KEY is not configured. "
            "Director was not called."
        )
        return

    try:
        proposal = run_bootstrap()
        path = save_proposal(proposal)

        print("DIRECTOR_BOOTSTRAP: PASS")
        print(f"proposal: {path.relative_to(ROOT)}")
        print(
            json.dumps(
                proposal.model_dump(),
                indent=2,
                ensure_ascii=False,
            )
        )

    except Exception as exc:
        print(
            "DIRECTOR_BOOTSTRAP: FAILED"
        )
        print(
            f"{type(exc).__name__}: {exc}"
        )


if __name__ == "__main__":
    main()
