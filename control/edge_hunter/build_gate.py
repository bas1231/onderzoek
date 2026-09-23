from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from . import autonomous_build_governance, prebuild_warrant

ROOT = Path(__file__).resolve().parents[2]


def _deny(*reasons: str) -> dict[str, Any]:
    return {
        "allowed": False,
        "decision": "DENY",
        "reasons": sorted(set(reasons)),
        "warrant_ref": None,
    }


def _load_object(path: Path, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _validate_common_authorization(
    authorization: dict[str, Any],
    policy: dict[str, Any],
    build_state: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []

    if build_state.get("builds_enabled") is not True:
        reasons.append("build_freeze_active")

    for flag, expected in policy["required_build_state_safety_flags"].items():
        if build_state.get(flag) is not expected:
            reasons.append(f"unsafe_build_state_flag:{flag}")

    objective = authorization.get("objective")
    if not isinstance(objective, str) or not objective.strip():
        reasons.append("missing_objective")

    build_kind = authorization.get("build_kind")
    if build_kind not in set(policy["allowed_build_kinds"]):
        reasons.append("build_kind_not_allowed")

    capabilities = authorization.get("capabilities")
    if not isinstance(capabilities, list):
        reasons.append("capabilities_not_list")
    else:
        if len(capabilities) > int(policy["max_capabilities"]):
            reasons.append("too_many_capabilities")

        if not all(
            isinstance(capability, str) and capability.strip()
            for capability in capabilities
        ):
            reasons.append("invalid_capability")
        else:
            if len(set(capabilities)) != len(capabilities):
                reasons.append("duplicate_capability")

            for capability in sorted(
                set(capabilities) & set(policy["forbidden_capabilities"])
            ):
                reasons.append(f"forbidden_capability:{capability}")

    return reasons


def _safe_warrant_path(root: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value:
        return None

    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        return None

    if (
        not relative.as_posix().startswith("knowledge/warrants/")
        or relative.suffix != ".json"
    ):
        return None

    candidate = (root / relative).resolve()
    warrant_root = (root / "knowledge/warrants").resolve()

    if candidate.parent != warrant_root:
        return None

    return candidate


def authorize_task(
    task: dict[str, Any],
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Fail-closed admission decision for local control-plane tasks.

    Research tasks remain unaffected. Infrastructure tasks must explicitly
    declare either a control-plane authorization or a candidate-build warrant.
    Mutating infrastructure tasks additionally follow the repository-wide
    Autonomous Build Protocol.
    """

    if not isinstance(task, dict):
        return _deny("task_not_object")

    task_class = task.get("task_class", "research")
    authorization = task.get("build_authorization")

    if task_class != "infrastructure":
        if authorization is not None:
            return _deny("build_authorization_on_non_infrastructure_task")

        return {
            "allowed": True,
            "decision": "NOT_REQUIRED",
            "reasons": [],
            "warrant_ref": None,
        }

    if not isinstance(authorization, dict):
        return _deny("missing_build_authorization")

    try:
        policy = _load_object(
            root / "control/edge_hunter/warrant_policy.json",
            "warrant policy",
        )
        build_state = _load_object(
            root / "control/BUILD_STATE.json",
            "build state",
        )
    except Exception as exc:
        return _deny(f"control_plane_config_error:{type(exc).__name__}")

    reasons = _validate_common_authorization(
        authorization,
        policy,
        build_state,
    )

    governance = autonomous_build_governance.validate_task(
        task,
        root=root,
    )
    if not governance["allowed"]:
        reasons.extend(governance["reasons"])

    mode = authorization.get("mode")

    if mode == "control_plane":
        if authorization.get("build_kind") != "control_plane":
            reasons.append(
                "control_plane_requires_control_plane_build_kind"
            )

        if authorization.get("warrant_ref") is not None:
            reasons.append("control_plane_must_not_have_warrant_ref")

        if reasons:
            return _deny(*reasons)

        return {
            "allowed": True,
            "decision": "ALLOW_CONTROL_PLANE_BUILD",
            "reasons": [],
            "warrant_ref": None,
        }

    if mode != "candidate":
        reasons.append("invalid_build_authorization_mode")
        return _deny(*reasons)

    if authorization.get("build_kind") == "control_plane":
        reasons.append("candidate_mode_cannot_use_control_plane_build_kind")

    hypothesis_id = task.get("hypothesis_id")
    if (
        not isinstance(hypothesis_id, str)
        or not prebuild_warrant.ID_RE.fullmatch(hypothesis_id)
    ):
        reasons.append("invalid_hypothesis_id")
        return _deny(*reasons)

    candidate_path = (
        root / "knowledge/candidates" / f"{hypothesis_id}.json"
    )
    if not candidate_path.exists():
        reasons.append("candidate_not_found")
        return _deny(*reasons)

    try:
        candidate = _load_object(candidate_path, "candidate")
    except Exception as exc:
        reasons.append(f"candidate_load_error:{type(exc).__name__}")
        return _deny(*reasons)

    if candidate.get("candidate_id") != hypothesis_id:
        reasons.append("candidate_id_mismatch")

    warrant_path = _safe_warrant_path(
        root,
        authorization.get("warrant_ref"),
    )
    if warrant_path is None:
        reasons.append("missing_or_unsafe_warrant_ref")
        return _deny(*reasons)

    if not warrant_path.exists():
        reasons.append("warrant_not_found")
        return _deny(*reasons)

    try:
        stored = _load_object(warrant_path, "stored warrant")
    except Exception as exc:
        reasons.append(f"warrant_load_error:{type(exc).__name__}")
        return _deny(*reasons)

    request = {
        "build_kind": authorization.get("build_kind"),
        "objective": authorization.get("objective"),
        "capabilities": authorization.get("capabilities"),
    }

    try:
        current = prebuild_warrant.evaluate(
            candidate,
            request,
            policy=policy,
            build_state=build_state,
        )
    except Exception as exc:
        reasons.append(f"warrant_recheck_error:{type(exc).__name__}")
        return _deny(*reasons)

    if current.get("decision") != "ALLOW_RESEARCH_BUILD":
        reasons.extend(current.get("reasons", ["current_warrant_denied"]))

    immutable_fields = (
        "candidate_id",
        "candidate_sha256",
        "request_sha256",
        "policy_sha256",
        "build_state_sha256",
        "decision",
        "decision_sha256",
        "build_kind",
        "capabilities",
    )
    for field in immutable_fields:
        if stored.get(field) != current.get(field):
            reasons.append(f"stale_or_tampered_warrant:{field}")

    if reasons:
        return _deny(*reasons)

    return {
        "allowed": True,
        "decision": "ALLOW_CANDIDATE_BUILD",
        "reasons": [],
        "warrant_ref": warrant_path.relative_to(root).as_posix(),
    }
