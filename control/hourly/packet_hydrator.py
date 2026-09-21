from __future__ import annotations

from pathlib import Path
from typing import Any
import json


ROOT = Path.cwd()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, obj: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(obj, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def evidence_ref(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_id": item.get("source_id"),
        "document_sha256": item.get("document_sha256"),
        "retrieved_at": item.get("retrieved_at"),
        "source_state": item.get("source_state"),
        "term": item.get("term"),
        "snippet": item.get("snippet"),
    }


def hydrate_packet(
    packet: dict[str, Any],
    routed: dict[str, Any] | None,
    routing_path: Path,
) -> dict[str, Any]:

    if not routed:
        packet["input_refs"] = []
        packet["routed_evidence"] = []
        packet["coverage_gaps"] = []
        packet["routing_status"] = "NO_ROUTE"
        return packet

    evidence = [
        evidence_ref(x)
        for x in routed.get("evidence", [])
        if isinstance(x, dict)
    ]

    packet["routed_evidence"] = evidence
    packet["coverage_gaps"] = list(
        routed.get("coverage_gaps", [])
    )
    packet["routing_status"] = routed.get(
        "status",
        "UNKNOWN",
    )

    # Reference provenance without inventing files per evidence item.
    packet["input_refs"] = (
        [str(routing_path.relative_to(ROOT))]
        if evidence else []
    )

    # Re-evaluate states previously assigned before hydration.
    if packet.get("status") in {
        "PENDING",
        "NO_EVIDENCE",
        "READY",
    }:
        packet["status"] = "PENDING"

    packet.pop("orchestrator_reason", None)
    packet.pop("orchestrator_updated_at_unix", None)

    return packet


def _watch_triage_item(finding: dict[str, Any]) -> dict[str, Any]:
    sources = [x for x in finding.get("sources", []) if isinstance(x, dict)]
    falsification = finding.get("falsification", {})
    return {
        "finding_id": finding.get("id"),
        "candidate_key": finding.get("candidate_key"),
        "status": "WATCH",
        "triage_only": True,
        "promotion_authority": False,
        "attack_mode": finding.get("attack_mode"),
        "claim": finding.get("claim"),
        "source_ids": sorted({str(x.get("source_id")) for x in sources if x.get("source_id")}),
        "public_trigger": finding.get("economic_model", {}).get("public_trigger"),
        "next_decisive_test": falsification.get("next_decisive_test"),
        "snippet": finding.get("snippet"),
        "execution_gate": {
            "research_only": True,
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "economic_conclusion": "NO_PROVEN_EDGE",
        },
    }


def apply_recon_watch_triage(
    packet_dir: Path,
    recon_run_path: Path | None,
) -> dict[str, Any]:
    if recon_run_path is None or not recon_run_path.exists():
        return {"watch_count": 0, "specialist_roles": [], "routed_items": 0}

    data = load_json(recon_run_path)
    findings = [
        x for x in data.get("findings", [])
        if isinstance(x, dict) and x.get("status") == "WATCH"
    ]
    by_role: dict[str, dict[str, dict[str, Any]]] = {}

    for finding in findings:
        triage = _watch_triage_item(finding)
        stable_id = str(
            triage.get("candidate_key")
            or triage.get("finding_id")
            or ""
        )
        for role in finding.get("falsification", {}).get("specialist_route", []):
            role = str(role)
            by_role.setdefault(role, {})[stable_id] = triage

    routed_items = 0
    ref = str(recon_run_path.relative_to(ROOT))
    for role, triage_by_id in by_role.items():
        path = packet_dir / (role + ".json")
        if not path.exists():
            continue
        packet = load_json(path)
        triage_items = list(triage_by_id.values())
        packet["recon_watch_triage"] = triage_items
        refs = list(packet.get("input_refs", []))
        if ref not in refs:
            refs.append(ref)
        packet["input_refs"] = refs
        if packet.get("status") in {"PENDING", "NO_EVIDENCE", "READY"}:
            packet["status"] = "PENDING"
        save_json(path, packet)
        routed_items += len(triage_items)

    return {
        "watch_count": len(findings),
        "specialist_roles": sorted(by_role),
        "routed_items": routed_items,
    }


def apply_recon_hunts(
    packet_dir: Path,
    hunt_plan_path: Path | None,
) -> dict[str, Any]:
    if hunt_plan_path is None or not hunt_plan_path.exists():
        return {"hunt_count": 0, "specialist_roles": [], "killer_candidates": []}

    data = load_json(hunt_plan_path)
    plans = [x for x in data.get("plans", []) if isinstance(x, dict)]
    by_role: dict[str, list[dict[str, Any]]] = {}
    killer_ids: list[str] = []

    for plan in plans:
        cid = plan.get("candidate_id")
        if cid:
            killer_ids.append(str(cid))
        for role in plan.get("specialist_route", []):
            by_role.setdefault(str(role), []).append(plan)

    for role, hunts in by_role.items():
        path = packet_dir / (role + ".json")
        if not path.exists():
            continue
        packet = load_json(path)
        packet["recon_hunts"] = hunts
        refs = list(packet.get("input_refs", []))
        ref = str(hunt_plan_path.relative_to(ROOT))
        if ref not in refs:
            refs.append(ref)
        packet["input_refs"] = refs
        if packet.get("status") in {"PENDING", "NO_EVIDENCE", "READY"}:
            packet["status"] = "PENDING"
        save_json(path, packet)

    killer = packet_dir / "prebuild_killer.json"
    if killer.exists() and killer_ids:
        packet = load_json(killer)
        packet["candidate_ids"] = sorted(set(killer_ids))
        packet["candidates"] = plans
        ref = str(hunt_plan_path.relative_to(ROOT))
        refs = list(packet.get("input_refs", []))
        if ref not in refs:
            refs.append(ref)
        packet["input_refs"] = refs
        if packet.get("status") in {"PENDING", "WAITING_FOR_DATA", "READY"}:
            packet["status"] = "PENDING"
        save_json(killer, packet)

    return {
        "hunt_count": len(plans),
        "specialist_roles": sorted(by_role),
        "killer_candidates": sorted(set(killer_ids)),
    }


def hydrate_run(
    routing_path: Path,
    packet_dir: Path,
    hunt_plan_path: Path | None = None,
    recon_run_path: Path | None = None,
) -> dict[str, Any]:

    routing_path = routing_path.resolve()
    packet_dir = packet_dir.resolve()

    routing = load_json(routing_path)
    changed = []

    for packet_path in sorted(packet_dir.glob("*.json")):
        if packet_path.name.startswith("_"):
            continue

        packet = load_json(packet_path)
        role = str(packet.get("agent_id", ""))

        # Only routed specialist roles are hydrated here.
        if role not in routing:
            continue

        packet = hydrate_packet(
            packet,
            routing.get(role),
            routing_path,
        )

        save_json(packet_path, packet)
        changed.append(role)

    # WATCH is triage-only and never enters the killer/proof chain. Infer the
    # Recon run from the packet run-id when hourly_cycle does not pass it.
    if recon_run_path is None:
        inferred = ROOT / "knowledge/runs/recon" / (packet_dir.name + ".json")
        recon_run_path = inferred if inferred.exists() else None
    watch_triage = apply_recon_watch_triage(packet_dir, recon_run_path)
    hunts = apply_recon_hunts(packet_dir, hunt_plan_path)

    return {
        "routing": str(routing_path.relative_to(ROOT)),
        "packet_dir": str(packet_dir.relative_to(ROOT)),
        "hydrated_roles": changed,
        "recon_watch_triage": watch_triage,
        "recon_hunts": hunts,
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        raise SystemExit(
            "usage: packet_hydrator.py ROUTING_JSON PACKET_DIR"
        )

    result = hydrate_run(
        Path(sys.argv[1]),
        Path(sys.argv[2]),
    )

    print(json.dumps(result, indent=2, sort_keys=True))
