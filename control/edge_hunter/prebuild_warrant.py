from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any
import json
import re

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "control/edge_hunter/warrant_policy.json"
BUILD_STATE_PATH = ROOT / "control/BUILD_STATE.json"
WARRANT_DIR = ROOT / "knowledge/warrants"

PHASES = [
    "DISCOVERED",
    "MECHANISM_DEFINED",
    "PREBUILD_KILLED",
    "DATA_READY",
    "DEVELOPMENT",
    "VALIDATION",
    "HOLDOUT",
    "INDEPENDENT_REPRODUCTION",
    "EXECUTION_REALITY",
    "SHADOW",
    "MICRO_LIVE_ELIGIBLE",
]
ID_RE = re.compile(r"^[A-Za-z0-9._:-]{3,160}$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return sha256(_canonical_bytes(value)).hexdigest()


def _safe_digest(value: Any) -> str | None:
    try:
        return _digest(value)
    except (TypeError, ValueError):
        return None


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _load_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    policy = _load_json_object(path, "warrant policy")
    required_keys = {
        "version",
        "minimum_phase",
        "allowed_candidate_decisions",
        "required_pass_gates",
        "required_nonempty_fields",
        "required_candidate_safety_flags",
        "required_build_state_safety_flags",
        "allowed_build_kinds",
        "forbidden_capabilities",
        "max_capabilities",
    }
    if policy.get("version") != 1 or not required_keys.issubset(policy):
        raise ValueError("unsupported or incomplete warrant policy")
    if policy["minimum_phase"] not in PHASES:
        raise ValueError("warrant policy has invalid minimum_phase")
    return policy


def _load_build_state(path: Path = BUILD_STATE_PATH) -> dict[str, Any]:
    state = _load_json_object(path, "build state")
    if state.get("version") != 1:
        raise ValueError("unsupported build state")
    return state


def _nonempty(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict, set)):
        return bool(value)
    return value is not None


def evaluate(
    candidate: dict[str, Any],
    request: dict[str, Any],
    *,
    policy: dict[str, Any] | None = None,
    build_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate a candidate-specific research build request.

    Candidate/request problems fail closed into DENY. A malformed control-plane
    policy or build-state object is treated as a configuration error.
    """
    policy = policy or _load_policy()
    build_state = build_state or _load_build_state()

    if not isinstance(policy, dict) or policy.get("version") != 1:
        raise ValueError("invalid warrant policy object")
    if not isinstance(build_state, dict) or build_state.get("version") != 1:
        raise ValueError("invalid build state object")

    reasons: list[str] = []

    if not isinstance(candidate, dict):
        candidate = {}
        reasons.append("candidate_not_object")
    if not isinstance(request, dict):
        request = {}
        reasons.append("request_not_object")

    candidate_hash = _safe_digest(candidate)
    request_hash = _safe_digest(request)
    policy_hash = _safe_digest(policy)
    build_state_hash = _safe_digest(build_state)
    if candidate_hash is None:
        reasons.append("candidate_not_json_serializable")
    if request_hash is None:
        reasons.append("request_not_json_serializable")
    if policy_hash is None or build_state_hash is None:
        raise ValueError("control-plane inputs must be JSON serializable")

    if build_state.get("builds_enabled") is not True:
        reasons.append("build_freeze_active")
    for flag, expected in policy["required_build_state_safety_flags"].items():
        if build_state.get(flag) is not expected:
            reasons.append(f"unsafe_build_state_flag:{flag}")

    cid = candidate.get("candidate_id")
    if not isinstance(cid, str) or not ID_RE.fullmatch(cid):
        reasons.append("invalid_candidate_id")

    phase = candidate.get("phase")
    minimum_phase = policy["minimum_phase"]
    if phase not in PHASES:
        reasons.append("invalid_phase")
    elif PHASES.index(phase) < PHASES.index(minimum_phase):
        reasons.append(f"phase_below_minimum:{minimum_phase}")

    decision = candidate.get("decision")
    if decision not in set(policy["allowed_candidate_decisions"]):
        reasons.append("candidate_decision_not_buildable")

    for field in policy["required_nonempty_fields"]:
        if not _nonempty(candidate.get(field)):
            reasons.append(f"missing_or_empty:{field}")

    gates = candidate.get("gates")
    if not isinstance(gates, dict):
        reasons.append("gates_not_object")
        gates = {}
    for gate_name in policy["required_pass_gates"]:
        if gates.get(gate_name) != "PASS":
            reasons.append(f"gate_not_pass:{gate_name}")

    for flag, expected in policy["required_candidate_safety_flags"].items():
        if candidate.get(flag) is not expected:
            reasons.append(f"unsafe_candidate_flag:{flag}")

    build_kind = request.get("build_kind")
    if build_kind not in set(policy["allowed_build_kinds"]):
        reasons.append("build_kind_not_allowed")

    objective = request.get("objective")
    if not isinstance(objective, str) or not objective.strip():
        reasons.append("missing_objective")

    raw_capabilities = request.get("capabilities")
    capabilities: list[str] = []
    if not isinstance(raw_capabilities, list):
        reasons.append("capabilities_not_list")
    else:
        if len(raw_capabilities) > int(policy["max_capabilities"]):
            reasons.append("too_many_capabilities")
        all_strings = all(
            isinstance(item, str) and bool(item.strip())
            for item in raw_capabilities
        )
        if not all_strings:
            reasons.append("invalid_capability")
        else:
            capabilities = raw_capabilities
            if len(set(capabilities)) != len(capabilities):
                reasons.append("duplicate_capability")
            for capability in sorted(
                set(capabilities) & set(policy["forbidden_capabilities"])
            ):
                reasons.append(f"forbidden_capability:{capability}")

    result = {
        "warrant_version": 1,
        "policy_version": policy["version"],
        "evaluated_at": _now(),
        "candidate_id": cid if isinstance(cid, str) else None,
        "candidate_sha256": candidate_hash,
        "request_sha256": request_hash,
        "policy_sha256": policy_hash,
        "build_state_sha256": build_state_hash,
        "decision": "DENY" if reasons else "ALLOW_RESEARCH_BUILD",
        "reasons": sorted(set(reasons)),
        "build_kind": build_kind,
        "capabilities": capabilities,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
    }
    result["decision_sha256"] = _digest(
        {k: v for k, v in result.items() if k not in {"evaluated_at", "decision_sha256"}}
    )
    return result


def issue(
    candidate: dict[str, Any],
    request: dict[str, Any],
    *,
    warrant_dir: Path = WARRANT_DIR,
    policy: dict[str, Any] | None = None,
    build_state: dict[str, Any] | None = None,
) -> Path:
    result = evaluate(candidate, request, policy=policy, build_state=build_state)
    cid = result.get("candidate_id") or "UNKNOWN"
    safe_cid = cid if isinstance(cid, str) and ID_RE.fullmatch(cid) else "UNKNOWN"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    suffix = result["decision_sha256"][:12]
    path = warrant_dir / f"{stamp}-{safe_cid}-{suffix}.json"
    warrant_dir.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path
