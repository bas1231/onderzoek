from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{2,119}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _result(allowed: bool, decision: str, reasons: list[str]) -> dict[str, Any]:
    return {
        "allowed": allowed,
        "decision": decision,
        "reasons": sorted(set(reasons)),
    }


def _load_policy(root: Path) -> dict[str, Any]:
    value = json.loads(
        (root / "control/AUTONOMOUS_BUILD_POLICY.json").read_text(
            encoding="utf-8"
        )
    )
    if not isinstance(value, dict):
        raise ValueError("autonomous build policy must be an object")
    return value


def _string_list(value: Any, *, allow_empty: bool = False) -> bool:
    if not isinstance(value, list):
        return False
    if not allow_empty and not value:
        return False
    return all(isinstance(item, str) and item.strip() for item in value)


def _safe_relative(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        return None
    text = path.as_posix().strip("/")
    if not text or text == ".":
        return None
    return text


def _within(path: str, allowed: str) -> bool:
    allowed = allowed.rstrip("/")
    return path == allowed or path.startswith(allowed + "/")


def _touches(path: str, protected: str) -> bool:
    return _within(path, protected) or _within(protected, path)


def _is_mutating(authorization: dict[str, Any], policy: dict[str, Any]) -> bool:
    capabilities = authorization.get("capabilities")
    if not isinstance(capabilities, list):
        return True
    read_only = set(policy.get("read_only_capabilities") or [])
    return any(capability not in read_only for capability in capabilities)


def _current_commit(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return None
    value = result.stdout.strip()
    if result.returncode != 0 or not SHA_RE.fullmatch(value):
        return None
    return value


def validate_task(
    task: dict[str, Any],
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Validate the universal autonomous-build contract.

    Legacy/read-only infrastructure tasks remain compatible. Any infrastructure
    task requesting a capability outside the read-only allowlist is considered
    mutating and must provide a complete build contract.
    """

    if not isinstance(task, dict):
        return _result(False, "DENY", ["task_not_object"])

    if task.get("task_class") != "infrastructure":
        return _result(True, "NOT_REQUIRED", [])

    authorization = task.get("build_authorization")
    if not isinstance(authorization, dict):
        return _result(False, "DENY", ["missing_build_authorization"])

    try:
        policy = _load_policy(root)
    except Exception as exc:
        return _result(
            False,
            "DENY",
            [f"autonomous_build_policy_error:{type(exc).__name__}"],
        )

    if not _is_mutating(authorization, policy):
        return _result(True, "ALLOW_READ_ONLY", [])

    contract = authorization.get("build_contract")
    if not isinstance(contract, dict):
        return _result(False, "DENY", ["missing_build_contract"])

    reasons: list[str] = []

    if contract.get("protocol_version") != policy.get("version"):
        reasons.append("build_contract_protocol_version_mismatch")

    build_id = contract.get("build_id")
    if not isinstance(build_id, str) or not ID_RE.fullmatch(build_id):
        reasons.append("invalid_build_id")

    objective = contract.get("objective")
    if not isinstance(objective, str) or not objective.strip():
        reasons.append("missing_build_contract_objective")
    elif authorization.get("objective") != objective:
        reasons.append("build_contract_objective_mismatch")

    source_commit = contract.get("source_commit")
    if not isinstance(source_commit, str) or not SHA_RE.fullmatch(source_commit):
        reasons.append("invalid_build_contract_source_commit")
    else:
        current_commit = _current_commit(root)
        if current_commit is None:
            reasons.append("build_contract_source_commit_unverifiable")
        elif current_commit != source_commit:
            reasons.append("build_contract_source_commit_mismatch")

    allowed_capabilities = contract.get("allowed_capabilities")
    if not _string_list(allowed_capabilities):
        reasons.append("invalid_allowed_capabilities")
        allowed_capabilities = []

    task_capabilities = authorization.get("capabilities")
    if not _string_list(task_capabilities, allow_empty=True):
        reasons.append("invalid_task_capabilities")
        task_capabilities = []

    for capability in sorted(set(task_capabilities) - set(allowed_capabilities)):
        reasons.append(f"capability_outside_build_contract:{capability}")

    allowed_paths = contract.get("allowed_paths")
    planned_paths = contract.get("planned_paths")
    if not _string_list(allowed_paths):
        reasons.append("invalid_allowed_paths")
        allowed_paths = []
    if not _string_list(planned_paths):
        reasons.append("invalid_planned_paths")
        planned_paths = []

    safe_allowed: list[str] = []
    for value in allowed_paths:
        safe = _safe_relative(value)
        if safe is None:
            reasons.append(f"unsafe_allowed_path:{value}")
        else:
            safe_allowed.append(safe)

    safe_planned: list[str] = []
    for value in planned_paths:
        safe = _safe_relative(value)
        if safe is None:
            reasons.append(f"unsafe_planned_path:{value}")
            continue
        safe_planned.append(safe)
        if safe_allowed and not any(
            _within(safe, allowed) for allowed in safe_allowed
        ):
            reasons.append(f"planned_path_outside_allowed_paths:{safe}")

    for field in (
        "acceptance_criteria",
        "non_goals",
    ):
        if not _string_list(contract.get(field), allow_empty=(field == "non_goals")):
            reasons.append(f"invalid_{field}")

    for field in (
        "independent_verification",
        "rollback_plan",
        "cleanup_plan",
    ):
        value = contract.get(field)
        if not isinstance(value, str) or not value.strip():
            reasons.append(f"invalid_{field}")

    max_attempts = contract.get("max_attempts")
    policy_max_attempts = int(policy.get("max_attempts", 3))
    if (
        not isinstance(max_attempts, int)
        or isinstance(max_attempts, bool)
        or max_attempts < 1
        or max_attempts > policy_max_attempts
    ):
        reasons.append("invalid_max_attempts")

    safety = contract.get("safety")
    if not isinstance(safety, dict):
        reasons.append("invalid_safety")
    else:
        for flag, expected in (policy.get("required_safety_flags") or {}).items():
            if safety.get(flag) is not expected:
                reasons.append(f"unsafe_build_contract_flag:{flag}")

    governance_change = contract.get("governance_change")
    if not isinstance(governance_change, bool):
        reasons.append("invalid_governance_change")
        governance_change = False

    protected_paths = [
        str(value) for value in policy.get("protected_paths") or []
    ]
    touches_protected = any(
        _touches(path, protected)
        for path in safe_planned
        for protected in protected_paths
    )

    governance_capability = str(
        policy.get("governance_capability") or "governance_change"
    )
    if touches_protected:
        if not governance_change:
            reasons.append("protected_path_requires_governance_change")
        if governance_capability not in task_capabilities:
            reasons.append("protected_path_requires_governance_capability")
        if governance_capability not in allowed_capabilities:
            reasons.append("governance_capability_not_in_contract")

    if reasons:
        return _result(False, "DENY", reasons)

    return _result(True, "ALLOW_GOVERNED_BUILD", [])


def validate_changed_paths(
    task: dict[str, Any],
    changed_paths: list[str],
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Post-build scope check against the frozen planned_paths allowlist."""

    base = validate_task(task, root=root)
    if not base["allowed"]:
        return base

    authorization = task.get("build_authorization") or {}
    contract = authorization.get("build_contract")
    if not isinstance(contract, dict):
        return _result(True, "NOT_REQUIRED", [])

    planned = [
        safe
        for value in contract.get("planned_paths") or []
        if (safe := _safe_relative(value)) is not None
    ]

    reasons: list[str] = []
    for value in changed_paths:
        safe = _safe_relative(value)
        if safe is None:
            reasons.append(f"unsafe_changed_path:{value}")
            continue
        if not any(_within(safe, allowed) for allowed in planned):
            reasons.append(f"changed_path_outside_plan:{safe}")

    if reasons:
        return _result(False, "DENY", reasons)
    return _result(True, "CHANGES_WITHIN_PLAN", [])
