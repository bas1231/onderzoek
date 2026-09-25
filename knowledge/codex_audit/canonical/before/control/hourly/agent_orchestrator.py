from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import importlib.util
import json
import sys
import time

try:
    from control.hourly.candidate_worker_routing import hydrate_candidate_routes
except ModuleNotFoundError:
    from candidate_worker_routing import hydrate_candidate_routes


ROOT = Path.cwd()
PACKETS = ROOT / "knowledge/runs/agent_packets"


def _load_architecture():
    path = ROOT / "control/hourly/research_os_architecture.py"
    spec = importlib.util.spec_from_file_location("research_os_architecture_orchestrator", path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


ARCH = _load_architecture()

# New E007 permanent roles plus legacy compatibility for historical runs/tests.
PRIMARY_ROLES = {
    "discovery",
    "market_research",
    "mechanics",
    "algebra",
    "red_team_pentest",
    "recon_scout",
    "scout",
    "settlement",
    "microstructure",
    "behavioral",
    "informed_flow",
    "weather_twc",
}

CONTROL_ROLES = {
    "research_director",
    "independent_reproducer",
    "prebuild_killer",
    "chief_falsifier",
}

VALID_STATES = {
    "PENDING",
    "READY",
    "RUNNING",
    "NO_EVIDENCE",
    "WAITING_FOR_DATA",
    "WAITING_FOR_RESULT",
    "RESULT_READY",
    "COMPLETED",
    "FAILED",
    "FALSIFIED",
    "PARKED",
}

PRIORITIES = {
    "P0": 0,
    "P1": 1,
    "P2": 2,
    "P3": 3,
}

SERIOUS_REPRO_PHASES = {
    "REPRODUCTION",
    "PROMOTION",
}


@dataclass(frozen=True)
class Decision:
    state: str
    priority: str
    reason: str


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, obj: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(obj, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def has_evidence(packet: dict[str, Any]) -> bool:
    return bool(
        packet.get("input_refs")
        or packet.get("notes")
        or packet.get("routed_evidence")
        or packet.get("evidence")
        or packet.get("recon_watch_triage")
        or packet.get("recon_hunts")
    )


def has_candidate(packet: dict[str, Any]) -> bool:
    return bool(
        packet.get("candidate_ids")
        or packet.get("candidates")
        or packet.get("survivors")
        or packet.get("reproduction_candidates")
    )


def _packet_validation_results(packet: dict[str, Any]) -> list[dict[str, Any]]:
    values = packet.get("validation_results")
    if not isinstance(values, list):
        ai_result = packet.get("ai_result")
        values = ai_result.get("validation_results") if isinstance(ai_result, dict) else []
    return [x for x in values if isinstance(x, dict)] if isinstance(values, list) else []


def _validated_ids(items: Any, required_status: str) -> list[str]:
    if not isinstance(items, list):
        return []
    out = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if str(item.get("status", "")).upper() != required_status:
            continue
        cid = item.get("candidate_id")
        if cid:
            out.append(str(cid))
    return sorted(set(out))


def _red_team_passes(packet: dict[str, Any]) -> tuple[list[str], list[str]]:
    quick: set[str] = set()
    deep: set[str] = set()
    modes = packet.get("red_team_modes")
    if not isinstance(modes, dict):
        modes = {}

    for result in _packet_validation_results(packet):
        if str(result.get("status", "")).upper() != "PASS":
            continue
        cid = str(result.get("candidate_id") or "")
        if not cid:
            continue
        mode = str(
            result.get("mode")
            or result.get("stage")
            or modes.get(cid)
            or "QUICK_KILL"
        ).upper()
        if mode == "DEEP_FALSIFICATION":
            deep.add(cid)
            quick.add(cid)
        else:
            quick.add(cid)
    return sorted(quick), sorted(deep)


PROOF_GATES = {
    "source_provenance",
    "point_in_time",
    "out_of_sample",
    "signal_edge",
    "market_edge",
    "execution_reality",
    "red_team_quick_kill",
    "red_team_deep_falsification",
    "independent_reproducer",
}

GATE_ALIASES = {
    "red_team_quick_kill": ("red_team_quick_kill", "prebuild_killer"),
    "red_team_deep_falsification": ("red_team_deep_falsification", "chief_falsifier"),
}


def _gate_pass(gates: dict[str, Any], gate: str) -> bool:
    aliases = GATE_ALIASES.get(gate, (gate,))
    return any(str(gates.get(alias, "")).upper() == "PASS" for alias in aliases)


def proof_gate(
    result: dict[str, Any],
    upstream_ids: set[str],
) -> tuple[bool, list[str]]:
    cid = str(result.get("candidate_id", ""))
    if not cid or cid not in upstream_ids:
        return False, ["candidate_not_upstream_validated"]
    if str(result.get("status", "")).upper() != "PASS":
        return False, ["independent_reproduction_not_pass"]

    gates = result.get("gates")
    if not isinstance(gates, dict):
        return False, ["missing_structured_gates"]

    failed = sorted(gate for gate in PROOF_GATES if not _gate_pass(gates, gate))

    economics = result.get("economics")
    if not isinstance(economics, dict):
        failed.append("missing_economics")
    else:
        for key in (
            "fees",
            "spread",
            "slippage",
            "fills",
            "settlement",
            "capacity",
        ):
            if key not in economics:
                failed.append("economics_" + key)
        if economics.get("net_edge") is None:
            failed.append("economics_net_edge")

    return not failed, failed


def _serious_reproduction_rows(candidate_queue: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(candidate_queue, dict):
        return []
    rows = candidate_queue.get("queue")
    if not isinstance(rows, list):
        return []
    selected = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        status = str(row.get("queue_status") or "").upper()
        phase = str(row.get("phase") or "").upper()
        if status == "PROMOTION_CANDIDATE" or phase in SERIOUS_REPRO_PHASES:
            selected.append(row)
    return selected


def ensure_transient_reproducer(
    run_dir: Path,
    candidate_queue: dict[str, Any] | None,
) -> list[str]:
    rows = _serious_reproduction_rows(candidate_queue)
    ids = sorted({str(row.get("candidate_id")) for row in rows if row.get("candidate_id")})
    path = run_dir / "independent_reproducer.json"
    if not ids:
        return []

    contract_path = ROOT / "agents/contracts/independent_reproducer.json"
    contract = load_json(contract_path)
    existing = load_json(path) if path.exists() else {}
    packet = dict(existing) if isinstance(existing, dict) else {}
    packet.update({
        "run_id": run_dir.name,
        "agent_id": "independent_reproducer",
        "status": "PENDING",
        "contract": contract,
        "reproduction_candidates": ids,
        "candidate_ids": ids,
        "blind": True,
        "transient": True,
        "originating_conclusions_withheld": True,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "openai_api": False,
    })
    refs = sorted({
        str(row.get("source_ref"))
        for row in rows
        if row.get("source_ref")
    })
    packet["input_refs"] = refs
    packet["blind_reproduction_interface"] = [
        {
            "candidate_id": row.get("candidate_id"),
            "phase": row.get("phase"),
            "queue_status": row.get("queue_status"),
            "open_question": row.get("open_question"),
            "next_decisive_test": row.get("next_decisive_test"),
            "source_ref": row.get("source_ref"),
        }
        for row in rows
        if row.get("candidate_id")
    ]
    save_json(path, packet)
    return ids


def propagate_validation(run_dir: Path) -> dict[str, Any]:
    # E007 six-domain path.
    red_path = run_dir / "red_team_pentest.json"
    reproducer_path = run_dir / "independent_reproducer.json"

    if red_path.exists():
        red = load_json(red_path)
        quick_pass, deep_pass = _red_team_passes(red)
        reproducer = load_json(reproducer_path) if reproducer_path.exists() else {}
        reproduction_candidates = [
            str(x) for x in reproducer.get("reproduction_candidates", []) if x
        ]
        upstream = set(reproduction_candidates).intersection(deep_pass)
        proof_candidates: list[str] = []
        proof_rejections: dict[str, list[str]] = {}
        for result in _packet_validation_results(reproducer):
            ok, reasons = proof_gate(result, upstream)
            cid = str(result.get("candidate_id") or "")
            if ok:
                proof_candidates.append(cid)
            elif cid:
                proof_rejections[cid] = reasons
        return {
            "architecture": "E007_SIX_DOMAIN",
            "quick_kill_pass": quick_pass,
            "deep_falsification_pass": deep_pass,
            "reproduction_candidates": reproduction_candidates,
            "proof_candidates": sorted(set(proof_candidates)),
            "proof_rejections": proof_rejections,
            "economic_conclusion": (
                "PROVEN_EDGE_CANDIDATE" if proof_candidates else "NO_PROVEN_EDGE"
            ),
        }

    # Legacy path remains readable for historical runs.
    killer_path = run_dir / "prebuild_killer.json"
    falsifier_path = run_dir / "chief_falsifier.json"
    killer = load_json(killer_path) if killer_path.exists() else {}
    falsifier = load_json(falsifier_path) if falsifier_path.exists() else {}
    reproducer = load_json(reproducer_path) if reproducer_path.exists() else {}
    killer_pass = _validated_ids(_packet_validation_results(killer), "PASS")
    falsifier_pass = _validated_ids(_packet_validation_results(falsifier), "PASS")
    upstream = set(killer_pass).intersection(falsifier_pass)
    proof_candidates = []
    proof_rejections = {}
    for result in _packet_validation_results(reproducer):
        ok, reasons = proof_gate(result, upstream)
        cid = str(result.get("candidate_id") or "")
        if ok:
            proof_candidates.append(cid)
        elif cid:
            proof_rejections[cid] = reasons
    return {
        "architecture": "LEGACY_COMPAT",
        "killer_pass": killer_pass,
        "falsifier_pass": falsifier_pass,
        "reproduction_candidates": [str(x) for x in reproducer.get("reproduction_candidates", []) if x],
        "proof_candidates": sorted(set(proof_candidates)),
        "proof_rejections": proof_rejections,
        "economic_conclusion": "PROVEN_EDGE_CANDIDATE" if proof_candidates else "NO_PROVEN_EDGE",
    }


def decide(packet: dict[str, Any]) -> Decision:
    role = str(packet.get("agent_id", ""))
    current = str(packet.get("status", "PENDING"))

    if current == "NO_EVIDENCE" and isinstance(packet.get("ai_result"), dict):
        return Decision(current, str(packet.get("priority", "P3")), "ai_result_preserved")

    if current in {
        "RUNNING",
        "WAITING_FOR_DATA",
        "WAITING_FOR_RESULT",
        "RESULT_READY",
        "COMPLETED",
        "FAILED",
        "FALSIFIED",
        "PARKED",
    }:
        return Decision(current, str(packet.get("priority", "P3")), "existing_state_preserved")

    if role == "red_team_pentest":
        if has_candidate(packet):
            return Decision("READY", "P2", "candidate_available_for_red_team")
        return Decision("WAITING_FOR_DATA", "P2", "no_candidate_available_for_red_team")

    if role in PRIMARY_ROLES:
        if has_candidate(packet):
            return Decision(
                "READY",
                "P3",
                "candidate_and_routed_evidence_available" if has_evidence(packet) else "candidate_assignment_available",
            )
        if has_evidence(packet):
            return Decision("READY", "P3", "routed_evidence_available")
        return Decision("NO_EVIDENCE", "P3", "no_routed_evidence")

    if role == "prebuild_killer":
        return Decision("READY", "P2", "candidate_available_for_prebuild_kill") if has_candidate(packet) else Decision("WAITING_FOR_DATA", "P2", "no_candidate_available")

    if role == "chief_falsifier":
        return Decision("READY", "P2", "survivor_available_for_falsification") if packet.get("survivors") else Decision("WAITING_FOR_DATA", "P2", "no_survivor_available")

    if role == "independent_reproducer":
        if packet.get("reproduction_candidates") or packet.get("survivors"):
            return Decision("READY", "P2", "serious_survivor_available_for_blind_reproduction")
        return Decision("WAITING_FOR_DATA", "P2", "no_serious_survivor_available")

    if role == "research_director":
        return Decision("READY", "P1", "director_closes_active_cycle")

    return Decision("PARKED", "P3", "unknown_agent_role")


def enrich_packet(path: Path) -> dict[str, Any]:
    packet = load_json(path)
    packet["live_trading"] = False
    packet["paid_actions"] = False
    packet["wallet_actions"] = False
    packet["openai_api"] = False

    decision = decide(packet)
    packet["status"] = decision.state
    packet["priority"] = decision.priority
    packet["orchestrator_reason"] = decision.reason
    packet["orchestrator_updated_at_unix"] = int(time.time())
    packet.setdefault("next_decisive_question", None)
    packet.setdefault("local_task_required", False)
    packet.setdefault("local_task_id", None)

    save_json(path, packet)
    return packet


def priority_key(packet: dict[str, Any]) -> tuple[int, int, str]:
    priority = str(packet.get("priority", "P3"))
    created = int(
        packet.get(
            "created_at_unix",
            packet.get("orchestrator_updated_at_unix", int(time.time())),
        )
    )
    return (
        PRIORITIES.get(priority, 99),
        created,
        str(packet.get("agent_id", "")),
    )


def orchestrate(
    run_dir: Path,
    candidate_queue: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not run_dir.is_dir():
        raise FileNotFoundError(run_dir)

    candidate_assignments = hydrate_candidate_routes(run_dir, candidate_queue)
    transient_candidates = ensure_transient_reproducer(run_dir, candidate_queue)
    validation = propagate_validation(run_dir)
    packets = []

    for path in sorted(run_dir.glob("*.json")):
        if path.name.startswith("_"):
            continue
        packets.append(enrich_packet(path))

    ordered = sorted(packets, key=priority_key)
    queue = [
        {
            "agent_id": packet.get("agent_id"),
            "status": packet.get("status"),
            "priority": packet.get("priority"),
            "reason": packet.get("orchestrator_reason"),
            "candidate_ids": packet.get("candidate_ids", []),
            "candidate_routing": packet.get("candidate_routing", []),
            "capabilities": sorted((packet.get("capability_work") or {}).keys()) if isinstance(packet.get("capability_work"), dict) else [],
            "red_team_modes": packet.get("red_team_modes", {}),
            "transient": bool(packet.get("transient", False)),
            "blind": bool(packet.get("blind", False)),
            "local_task_required": packet.get("local_task_required", False),
        }
        for packet in ordered
    ]

    summary = {
        "schema": "PVA_ORCHESTRATION_E007_V1",
        "run_id": run_dir.name,
        "architecture": "E007_SIX_DOMAIN",
        "permanent_agents": list(ARCH.PERMANENT_AGENTS),
        "transient_reproducer_candidates": transient_candidates,
        "guardrails": {
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "openai_api": False,
        },
        "candidate_routing": candidate_assignments,
        "queue": queue,
        "validation_pipeline": validation,
    }

    save_json(run_dir / "_orchestration.json", summary)
    return summary


def latest_run_dir() -> Path:
    if not PACKETS.exists():
        raise FileNotFoundError(PACKETS)
    runs = sorted(path for path in PACKETS.iterdir() if path.is_dir())
    if not runs:
        raise RuntimeError("no agent packet runs found")
    return runs[-1]


if __name__ == "__main__":
    run_dir = latest_run_dir()
    result = orchestrate(run_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
