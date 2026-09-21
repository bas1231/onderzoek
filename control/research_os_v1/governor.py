from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .policy import load_governor_policy


@dataclass(frozen=True)
class GovernorDecision:
    decision: str
    reason: str
    rule_id: str | None
    admissible: bool
    requires_user_approval: bool


def _decision(decision: str, reason: str, rule_id: str | None) -> GovernorDecision:
    return GovernorDecision(
        decision=decision,
        reason=reason,
        rule_id=rule_id,
        admissible=decision == "ALLOW",
        requires_user_approval=decision == "BLOCK_USER_APPROVAL",
    )


def classify(action: dict[str, Any], policy: dict[str, Any] | None = None) -> GovernorDecision:
    """Deterministically classify one proposed action.

    The action must explicitly declare `kind`. Unknown actions fail closed.
    No free-form LLM interpretation is used here.
    """
    policy = policy or load_governor_policy()
    kind = str(action.get("kind") or "").strip()
    rules = {str(r.get("match")): r for r in policy.get("rules", []) if isinstance(r, dict)}

    if not kind:
        return _decision("BLOCK", "missing_action_kind", None)

    rule = rules.get(kind)
    if rule is None:
        return _decision(
            str(policy.get("default_action", "BLOCK_UNLESS_CLASSIFIED")),
            f"unclassified_action:{kind}",
            None,
        )

    decision = str(rule.get("decision") or "BLOCK")
    rule_id = str(rule.get("id")) if rule.get("id") else None

    if decision == "ALLOW":
        requirements = [str(x) for x in rule.get("requirements", [])]
        missing = []
        if "provenance" in requirements and not action.get("provenance"):
            missing.append("provenance")
        if "point_in_time" in requirements and not action.get("point_in_time"):
            missing.append("point_in_time")
        if "branch_is_not_main" in requirements and action.get("branch") in {None, "", "main"}:
            missing.append("branch_is_not_main")
        if "no_secrets" in requirements and action.get("contains_secrets") is not False:
            missing.append("no_secrets")
        if missing:
            return _decision("BLOCK", "missing_requirements:" + ",".join(sorted(missing)), rule_id)

    return _decision(decision, f"matched:{kind}", rule_id)
