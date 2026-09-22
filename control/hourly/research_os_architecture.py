from __future__ import annotations

from dataclasses import dataclass
from typing import Any


PERMANENT_AGENTS = (
    "discovery",
    "market_research",
    "mechanics",
    "algebra",
    "red_team_pentest",
    "research_director",
)

DYNAMIC_WORKERS = tuple(
    role for role in PERMANENT_AGENTS if role != "research_director"
)

TRANSIENT_AGENTS = ("independent_reproducer",)

# Legacy specialist identities remain as capabilities. They are deliberately
# not permanent runtime agents after E007.
CAPABILITY_TO_DOMAIN = {
    "recon_scout": "discovery",
    "scout": "discovery",
    "weather_twc": "market_research",
    "behavioral": "market_research",
    "informed_flow": "market_research",
    "settlement": "mechanics",
    "microstructure": "mechanics",
    "algebra": "algebra",
    "prebuild_killer": "red_team_pentest",
    "chief_falsifier": "red_team_pentest",
    "research_director": "research_director",
    "independent_reproducer": "independent_reproducer",
}

DOMAIN_CAPABILITIES = {
    "discovery": ("scout", "recon_scout"),
    "market_research": ("weather_twc", "behavioral", "informed_flow"),
    "mechanics": ("settlement", "microstructure"),
    "algebra": ("algebra",),
    "red_team_pentest": ("prebuild_killer", "chief_falsifier"),
    "research_director": ("research_director",),
    "independent_reproducer": ("independent_reproducer",),
}

# The two Discovery lanes are protected from being collapsed into one source
# of ideas. They share one permanent packet/worker but retain separate inputs,
# provenance and output labels.
PROTECTED_DISCOVERY_LANES = (
    "primary_scout",
    "recon_scout",
)

TASK_SHAPES = {
    "LOW_SEQUENTIAL": {
        "max_parallel_workers": 1,
        "dependencies": "sequential",
    },
    "MEDIUM_PARTIAL": {
        "max_parallel_workers": 3,
        "dependencies": "partial",
    },
    "HIGH_INDEPENDENT": {
        "max_parallel_workers": 5,
        "dependencies": "independent",
    },
}

SCHEDULER_PRIORITY = (
    "GOVERNOR_ADMISSIBLE_ONLY",
    "DECISIVE_SEMANTIC_OR_SOURCE_KILL_CHECK",
    "CHEAP_DECISIVE_FALSIFICATION",
    "POINT_IN_TIME_OR_EXECUTION_EVIDENCE",
    "MULTI_DEPENDENCY_UNLOCK",
    "TIME_SENSITIVE_EVIDENCE",
    "NOVEL_EVIDENCE",
    "AGE_TIE_BREAK",
)

RED_TEAM_MODES = (
    "QUICK_KILL",
    "DEEP_FALSIFICATION",
)


@dataclass(frozen=True)
class TaskShape:
    name: str
    max_parallel_workers: int
    dependencies: str
    uncertainty: str
    time_sensitivity: str
    novelty: str
    expected_decision_value: str


def domain_for_capability(capability: str) -> str:
    return CAPABILITY_TO_DOMAIN.get(capability, capability)


def capabilities_for_domain(domain: str) -> tuple[str, ...]:
    return tuple(DOMAIN_CAPABILITIES.get(domain, (domain,)))


def resolve_packet_role(capability: str, available_roles: set[str]) -> str | None:
    """Prefer the six-domain packet, but keep old packet layouts testable/readable."""
    domain = domain_for_capability(capability)
    if domain in available_roles:
        return domain
    if capability in available_roles:
        return capability
    return None


def red_team_mode(candidate: dict[str, Any]) -> str:
    phase = str(candidate.get("phase") or "").upper()
    status = str(candidate.get("queue_status") or "").upper()
    if status in {"RESULT_READY", "NEEDS_REVISION", "PROMOTION_CANDIDATE"}:
        return "DEEP_FALSIFICATION"
    if phase in {
        "VALIDATED",
        "PROSPECTIVE",
        "PROSPECTIVE_VALIDATION",
        "REPRODUCTION",
        "PROMOTION",
    }:
        return "DEEP_FALSIFICATION"
    return "QUICK_KILL"


def classify_task_shape(packet: dict[str, Any]) -> TaskShape:
    role = str(packet.get("agent_id") or "")
    candidates = [x for x in packet.get("candidate_ids", []) if x]
    capability_work = packet.get("capability_work", {})
    capability_count = (
        len([k for k, v in capability_work.items() if v])
        if isinstance(capability_work, dict)
        else 0
    )

    if role in {"red_team_pentest", "independent_reproducer"}:
        name = "LOW_SEQUENTIAL"
        uncertainty = "semantic/economic"
    elif len(candidates) >= 2 or capability_count >= 2 or role == "discovery":
        name = "HIGH_INDEPENDENT"
        uncertainty = "source/semantic"
    else:
        name = "MEDIUM_PARTIAL"
        uncertainty = "source/semantic/economic"

    spec = TASK_SHAPES[name]
    time_sensitivity = (
        "high"
        if role == "market_research"
        and isinstance(capability_work, dict)
        and bool(capability_work.get("weather_twc"))
        else "normal"
    )
    novelty = "high" if role == "discovery" else "normal"
    expected = "high" if candidates else "medium"
    return TaskShape(
        name=name,
        max_parallel_workers=int(spec["max_parallel_workers"]),
        dependencies=str(spec["dependencies"]),
        uncertainty=uncertainty,
        time_sensitivity=time_sensitivity,
        novelty=novelty,
        expected_decision_value=expected,
    )


def scheduler_bucket(packet: dict[str, Any]) -> str:
    role = str(packet.get("agent_id") or "")
    if role == "red_team_pentest":
        return "CHEAP_DECISIVE_FALSIFICATION"
    if role == "algebra":
        return "DECISIVE_SEMANTIC_OR_SOURCE_KILL_CHECK"
    if role == "mechanics":
        return "POINT_IN_TIME_OR_EXECUTION_EVIDENCE"
    if role == "market_research":
        work = packet.get("capability_work", {})
        if isinstance(work, dict) and work.get("weather_twc"):
            return "TIME_SENSITIVE_EVIDENCE"
        return "MULTI_DEPENDENCY_UNLOCK"
    if role == "discovery":
        return "NOVEL_EVIDENCE"
    return "AGE_TIE_BREAK"
