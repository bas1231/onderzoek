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


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def classify(action: dict[str, Any], policy: dict[str, Any] | None = None) -> GovernorDecision:
    """Deterministically classify one proposed action.

    The action must explicitly declare a real string `kind`. Unknown or
    malformed actions fail closed. Requirement flags use exact booleans rather
    than Python truthiness so values such as integer 1 cannot impersonate True.
    """
    if not isinstance(action, dict):
        return _decision("BLOCK", "action_must_be_object", None)

    policy = policy or load_governor_policy()
    if not isinstance(policy, dict):
        return _decision("BLOCK", "policy_must_be_object", None)

    raw_kind = action.get("kind")
    if not _nonempty_string(raw_kind):
        return _decision("BLOCK", "missing_or_invalid_action_kind", None)
    kind = raw_kind.strip()

    rules: dict[str, dict[str, Any]] = {}
    for index, rule in enumerate(policy.get("rules", [])):
        if not isinstance(rule, dict):
            return _decision("BLOCK", f"invalid_policy_rule:{index}", None)
        match = rule.get("match")
        if not _nonempty_string(match):
            return _decision("BLOCK", f"invalid_policy_match:{index}", None)
        match = match.strip()
        if match in rules:
            return _decision("BLOCK", f"duplicate_policy_match:{match}", None)
        rules[match] = rule

    rule = rules.get(kind)
    if rule is None:
        default = policy.get("default_action", "BLOCK_UNLESS_CLASSIFIED")
        if not _nonempty_string(default):
            default = "BLOCK"
        return _decision(default.strip(), f"unclassified_action:{kind}", None)

    raw_decision = rule.get("decision")
    decision = raw_decision.strip() if _nonempty_string(raw_decision) else "BLOCK"
    raw_rule_id = rule.get("id")
    rule_id = raw_rule_id.strip() if _nonempty_string(raw_rule_id) else None

    if decision == "ALLOW":
        raw_requirements = rule.get("requirements", [])
        if not isinstance(raw_requirements, list) or not all(
            _nonempty_string(item) for item in raw_requirements
        ):
            return _decision("BLOCK", "invalid_policy_requirements", rule_id)
        requirements = [item.strip() for item in raw_requirements]
        missing: list[str] = []

        if "provenance" in requirements and action.get("provenance") is not True:
            missing.append("provenance")
        if "point_in_time" in requirements and action.get("point_in_time") is not True:
            missing.append("point_in_time")
        if "branch_is_not_main" in requirements:
            branch = action.get("branch")
            if not _nonempty_string(branch) or branch.strip() == "main":
                missing.append("branch_is_not_main")
        if "no_secrets" in requirements and action.get("contains_secrets") is not False:
            missing.append("no_secrets")

        if missing:
            return _decision(
                "BLOCK",
                "missing_requirements:" + ",".join(sorted(missing)),
                rule_id,
            )

    return _decision(decision, f"matched:{kind}", rule_id)
