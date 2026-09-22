from __future__ import annotations

from pathlib import Path
from typing import Any
import importlib.util
import json
import sys


ROOT = Path.cwd()


def _load_architecture():
    path = ROOT / "control/hourly/research_os_architecture.py"
    spec = importlib.util.spec_from_file_location("research_os_architecture_hydrator", path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


ARCH = _load_architecture()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, obj: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(obj, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def evidence_ref(item: dict[str, Any], capability: str | None = None) -> dict[str, Any]:
    out = {
        "source_id": item.get("source_id"),
        "document_sha256": item.get("document_sha256"),
        "retrieved_at": item.get("retrieved_at"),
        "source_state": item.get("source_state"),
        "term": item.get("term"),
        "snippet": item.get("snippet"),
    }
    if capability:
        out["capability"] = capability
    return out


def available_roles(packet_dir: Path) -> set[str]:
    return {
        path.stem
        for path in packet_dir.glob("*.json")
        if not path.name.startswith("_")
    }


def _resolve_packet(packet_dir: Path, capability: str) -> tuple[str, Path] | None:
    role = ARCH.resolve_packet_role(capability, available_roles(packet_dir))
    if not role:
        return None
    path = packet_dir / f"{role}.json"
    return (role, path) if path.exists() else None


def _dedup_dicts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    for item in items:
        key = json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
        selected[key] = item
    return [selected[key] for key in sorted(selected)]


def _dedup_candidate_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    for item in items:
        cid = str(item.get("candidate_key") or item.get("candidate_id") or item.get("finding_id") or "")
        key = cid or json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
        selected.setdefault(key, item)
    return [selected[key] for key in sorted(selected)]


def _capability_bucket(packet: dict[str, Any], capability: str) -> dict[str, Any]:
    work = packet.get("capability_work")
    if not isinstance(work, dict):
        work = {}
    bucket = work.get(capability)
    if not isinstance(bucket, dict):
        bucket = {}
    work[capability] = bucket
    packet["capability_work"] = work
    return bucket


def _mark_pending(packet: dict[str, Any]) -> None:
    if packet.get("status") in {"PENDING", "NO_EVIDENCE", "READY"}:
        packet["status"] = "PENDING"
    packet.pop("orchestrator_reason", None)
    packet.pop("orchestrator_updated_at_unix", None)


def hydrate_capability(
    packet: dict[str, Any],
    capability: str,
    routed: dict[str, Any] | None,
    routing_path: Path,
) -> dict[str, Any]:
    bucket = _capability_bucket(packet, capability)
    if not routed:
        bucket["routed_evidence"] = []
        bucket["coverage_gaps"] = []
        bucket["routing_status"] = "NO_ROUTE"
        return packet

    evidence = [
        evidence_ref(x, capability)
        for x in routed.get("evidence", [])
        if isinstance(x, dict)
    ]
    bucket["routed_evidence"] = evidence
    bucket["coverage_gaps"] = list(routed.get("coverage_gaps", []))
    bucket["routing_status"] = routed.get("status", "UNKNOWN")

    flat = [x for x in packet.get("routed_evidence", []) if isinstance(x, dict)]
    flat.extend(evidence)
    packet["routed_evidence"] = _dedup_dicts(flat)

    gaps = packet.get("coverage_gaps_by_capability")
    if not isinstance(gaps, dict):
        gaps = {}
    gaps[capability] = list(bucket["coverage_gaps"])
    packet["coverage_gaps_by_capability"] = gaps
    packet["coverage_gaps"] = sorted({
        str(gap)
        for values in gaps.values()
        if isinstance(values, list)
        for gap in values
    })

    if evidence:
        ref = str(routing_path.relative_to(ROOT))
        refs = [str(x) for x in packet.get("input_refs", [])]
        if ref not in refs:
            refs.append(ref)
        packet["input_refs"] = refs
    _mark_pending(packet)

    if packet.get("agent_id") == "discovery" and capability in {"scout", "recon_scout"}:
        lanes = packet.get("discovery_lanes")
        if not isinstance(lanes, dict):
            lanes = {}
        lane_name = "primary_scout" if capability == "scout" else "recon_scout"
        lanes[lane_name] = {
            "capability": capability,
            "routed_evidence": evidence,
            "coverage_gaps": list(bucket["coverage_gaps"]),
            "routing_status": bucket["routing_status"],
        }
        packet["discovery_lanes"] = lanes

    return packet


def hydrate_packet(
    packet: dict[str, Any],
    routed: dict[str, Any] | None,
    routing_path: Path,
) -> dict[str, Any]:
    """Legacy direct helper retained for historical regression tests/tools."""
    capability = str(packet.get("agent_id") or "unknown")
    hydrated = hydrate_capability(packet, capability, routed, routing_path)
    # Historical callers expect evidence objects without a capability label.
    hydrated["routed_evidence"] = [
        {k: v for k, v in item.items() if k != "capability"}
        for item in hydrated.get("routed_evidence", [])
    ]
    return hydrated


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
        return {"watch_count": 0, "domain_roles": [], "specialist_roles": [], "routed_items": 0}

    data = load_json(recon_run_path)
    findings = [
        x for x in data.get("findings", [])
        if isinstance(x, dict) and x.get("status") == "WATCH"
    ]
    routed_items = 0
    touched: set[str] = set()
    routed_keys: set[tuple[str, str]] = set()
    ref = str(recon_run_path.relative_to(ROOT))

    for finding in findings:
        triage = _watch_triage_item(finding)
        stable_id = str(triage.get("candidate_key") or triage.get("finding_id") or "")
        for raw_capability in finding.get("falsification", {}).get("specialist_route", []):
            capability = str(raw_capability)
            resolved = _resolve_packet(packet_dir, capability)
            if not resolved:
                continue
            role, path = resolved
            dedup_key = (role + ":" + capability, stable_id)
            if dedup_key in routed_keys:
                continue
            routed_keys.add(dedup_key)
            packet = load_json(path)
            item = dict(triage)
            item["capability"] = capability

            bucket = _capability_bucket(packet, capability)
            current = [x for x in bucket.get("recon_watch_triage", []) if isinstance(x, dict)]
            current.append(item)
            bucket["recon_watch_triage"] = _dedup_candidate_items(current)

            top = [x for x in packet.get("recon_watch_triage", []) if isinstance(x, dict)]
            top.append(item)
            packet["recon_watch_triage"] = _dedup_candidate_items(top)

            refs = [str(x) for x in packet.get("input_refs", [])]
            if ref not in refs:
                refs.append(ref)
            packet["input_refs"] = refs
            _mark_pending(packet)
            save_json(path, packet)
            routed_items += 1
            touched.add(role)

    roles = sorted(touched)
    return {
        "watch_count": len(findings),
        "domain_roles": roles,
        "specialist_roles": roles,
        "routed_items": routed_items,
    }


def apply_recon_hunts(
    packet_dir: Path,
    hunt_plan_path: Path | None,
) -> dict[str, Any]:
    if hunt_plan_path is None or not hunt_plan_path.exists():
        return {"hunt_count": 0, "domain_roles": [], "specialist_roles": [], "killer_candidates": []}

    data = load_json(hunt_plan_path)
    plans = [x for x in data.get("plans", []) if isinstance(x, dict)]
    touched: set[str] = set()
    killer_ids: list[str] = []
    ref = str(hunt_plan_path.relative_to(ROOT))

    for plan in plans:
        cid = plan.get("candidate_id")
        if cid:
            killer_ids.append(str(cid))
        for raw_capability in plan.get("specialist_route", []):
            capability = str(raw_capability)
            resolved = _resolve_packet(packet_dir, capability)
            if not resolved:
                continue
            role, path = resolved
            packet = load_json(path)
            item = dict(plan)
            item["capability"] = capability

            bucket = _capability_bucket(packet, capability)
            hunts = [x for x in bucket.get("recon_hunts", []) if isinstance(x, dict)]
            hunts.append(item)
            bucket["recon_hunts"] = _dedup_candidate_items(hunts)

            top = [x for x in packet.get("recon_hunts", []) if isinstance(x, dict)]
            top.append(item)
            packet["recon_hunts"] = _dedup_candidate_items(top)
            refs = [str(x) for x in packet.get("input_refs", [])]
            if ref not in refs:
                refs.append(ref)
            packet["input_refs"] = refs
            _mark_pending(packet)
            save_json(path, packet)
            touched.add(role)

    if killer_ids:
        resolved = _resolve_packet(packet_dir, "prebuild_killer")
        if resolved:
            role, path = resolved
            packet = load_json(path)
            ids = {str(x) for x in packet.get("candidate_ids", []) if x}
            ids.update(killer_ids)
            packet["candidate_ids"] = sorted(ids)
            packet["candidates"] = plans
            bucket = _capability_bucket(packet, "prebuild_killer")
            bucket["candidate_ids"] = sorted(ids)
            bucket["recon_hunts"] = plans
            modes = packet.get("red_team_modes")
            if not isinstance(modes, dict):
                modes = {}
            for cid in killer_ids:
                modes[str(cid)] = "QUICK_KILL"
            packet["red_team_modes"] = modes
            refs = [str(x) for x in packet.get("input_refs", [])]
            if ref not in refs:
                refs.append(ref)
            packet["input_refs"] = refs
            _mark_pending(packet)
            save_json(path, packet)
            touched.add(role)

    roles = sorted(touched)
    return {
        "hunt_count": len(plans),
        "domain_roles": roles,
        "specialist_roles": roles,
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
    changed: set[str] = set()
    hydrated_capabilities: list[str] = []

    for capability, routed in sorted(routing.items()):
        resolved = _resolve_packet(packet_dir, str(capability))
        if not resolved:
            continue
        role, packet_path = resolved
        packet = load_json(packet_path)
        packet = hydrate_capability(packet, str(capability), routed, routing_path)
        save_json(packet_path, packet)
        changed.add(role)
        hydrated_capabilities.append(str(capability))

    if recon_run_path is None:
        inferred = ROOT / "knowledge/runs/recon" / (packet_dir.name + ".json")
        recon_run_path = inferred if inferred.exists() else None
    watch_triage = apply_recon_watch_triage(packet_dir, recon_run_path)
    hunts = apply_recon_hunts(packet_dir, hunt_plan_path)

    return {
        "routing": str(routing_path.relative_to(ROOT)),
        "packet_dir": str(packet_dir.relative_to(ROOT)),
        "hydrated_roles": sorted(changed),
        "hydrated_capabilities": sorted(set(hydrated_capabilities)),
        "recon_watch_triage": watch_triage,
        "recon_hunts": hunts,
        "architecture": "E007_SIX_DOMAIN",
    }


if __name__ == "__main__":
    import sys as _sys

    if len(_sys.argv) != 3:
        raise SystemExit("usage: packet_hydrator.py ROUTING_JSON PACKET_DIR")

    result = hydrate_run(Path(_sys.argv[1]), Path(_sys.argv[2]))
    print(json.dumps(result, indent=2, sort_keys=True))
