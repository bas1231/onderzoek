from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib
import json

ROOT = Path.cwd()
ELIGIBLE_RECON_STATES = {"HUNT", "PROVE"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def candidate_id(candidate_key: str) -> str:
    return "AUTO-RECON-" + hashlib.sha256(candidate_key.encode()).hexdigest()[:20]


def _source_history(item: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for source in item.get("observation_history", []):
        if not isinstance(source, dict):
            continue
        rows.append({
            "source_id": source.get("source_id"),
            "document_sha256": source.get("document_sha256"),
            "observed_at": source.get("observed_at"),
            "economic_context_count": source.get("economic_context_count"),
        })
    if not rows:
        for source in item.get("sources", []):
            if not isinstance(source, dict):
                continue
            rows.append({
                "source_id": source.get("source_id"),
                "document_sha256": source.get("document_sha256"),
                "observed_at": source.get("point_in_time"),
                "economic_context_count": item.get("quality", {}).get("economic_context_count"),
            })
    dedup: dict[tuple[Any, Any], dict[str, Any]] = {}
    for row in rows:
        dedup[(row.get("source_id"), row.get("document_sha256"))] = row
    return list(dedup.values())


def eligible(item: dict[str, Any]) -> tuple[bool, str]:
    if not isinstance(item, dict):
        return False, "not_object"
    status = str(item.get("status") or "").upper()
    if status not in ELIGIBLE_RECON_STATES:
        return False, "status_not_hunt_or_prove"
    key = item.get("candidate_key")
    if not isinstance(key, str) or not key:
        return False, "candidate_key_missing"
    gate = item.get("hunt_gate")
    if not isinstance(gate, dict) or gate.get("passes") is not True:
        return False, "hunt_gate_not_passed"
    history = _source_history(item)
    independent_sources = {str(x.get("source_id")) for x in history if x.get("source_id")}
    if len(history) < 2 or len(independent_sources) < 2:
        return False, "insufficient_independent_evidence"
    model = item.get("economic_model")
    falsification = item.get("falsification")
    if not isinstance(model, dict) or not model.get("public_trigger"):
        return False, "public_trigger_missing"
    if not isinstance(falsification, dict) or not str(falsification.get("next_decisive_test") or "").strip():
        return False, "decisive_test_missing"
    return True, "eligible"


def build_candidate(item: dict[str, Any], created_at: str) -> dict[str, Any]:
    key = str(item["candidate_key"])
    cid = candidate_id(key)
    falsification = item["falsification"]
    model = item["economic_model"]
    history = _source_history(item)
    source_ids = sorted({str(x["source_id"]) for x in history if x.get("source_id")})
    attack_mode = str(item.get("attack_mode") or "UNKNOWN")
    trigger = str(model.get("public_trigger") or "")
    claim = str(item.get("claim") or "Autonomous Recon HUNT; mechanism unproven.")
    next_test = str(falsification["next_decisive_test"]).strip()
    return {
        "candidate_id": cid,
        "created_at": created_at,
        "updated_at": created_at,
        "provenance": "AUTONOMOUS_RECON_HUNT",
        "provenance_note": (
            "Deterministically created from a persisted Recon HUNT/PROVE that passed the "
            "multi-source hunt gate. Creation is not economic promotion and proves no edge."
        ),
        "origin_recon_candidate_key": key,
        "origin_recon_finding_id": item.get("id"),
        "origin_recon_status": str(item.get("status") or "").upper(),
        "lane": attack_mode.lower(),
        "phase": "DISCOVERED",
        "decision": "UNPROVEN",
        "scientific_status": "NO_PROVEN_EDGE",
        "queue_status": "NEEDS_DIRECTOR",
        "priority": "P2",
        "mechanism": claim + " Public trigger: " + trigger + ".",
        "open_question": next_test,
        "next_decisive_test": next_test,
        "needed_data": list(falsification.get("required_data") or []),
        "active_experiment_ids": [],
        "prospective_protocols": [],
        "evidence_refs": [],
        "resume_condition": None,
        "resurrection_condition": None,
        "stop_condition": None,
        "recon_provenance": {
            "attack_mode": attack_mode,
            "public_trigger": trigger,
            "specialist_route": list(falsification.get("specialist_route") or []),
            "quality": item.get("quality", {}),
            "hunt_gate": item.get("hunt_gate", {}),
            "source_ids": source_ids,
            "observations": history,
            "snippet": item.get("snippet"),
        },
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "openai_api": False,
    }


def promote(run_id: str, *, root: Path | None = None, timestamp: str | None = None) -> tuple[dict[str, Any], Path]:
    root = Path(root or ROOT)
    watchlist_path = root / "knowledge/recon/watchlist.json"
    candidates_dir = root / "knowledge/candidates"
    receipt_path = root / "knowledge/runs" / f"{run_id}-recon-candidate-promotions.json"
    watch = load_json(watchlist_path, {"items": []})
    items = watch.get("items", [])
    if not isinstance(items, list):
        raise ValueError("RECON_WATCHLIST_ITEMS_INVALID")

    existing_by_key: dict[str, list[tuple[Path, dict[str, Any]]]] = {}
    if candidates_dir.exists():
        for path in sorted(candidates_dir.glob("*.json")):
            if path.is_symlink():
                raise ValueError("CANDIDATE_SYMLINK")
            obj = load_json(path, {})
            key = obj.get("origin_recon_candidate_key") if isinstance(obj, dict) else None
            if isinstance(key, str) and key:
                existing_by_key.setdefault(key, []).append((path, obj))
    duplicates = {key: rows for key, rows in existing_by_key.items() if len(rows) > 1}
    if duplicates:
        raise ValueError("DUPLICATE_RECON_CANDIDATE_PROVENANCE")

    created = []
    skipped_existing = []
    ineligible = []
    ts = timestamp or now_iso()

    for item in sorted((x for x in items if isinstance(x, dict)), key=lambda x: str(x.get("candidate_key") or x.get("id") or "")):
        ok, reason = eligible(item)
        key = item.get("candidate_key")
        if not ok:
            ineligible.append({"candidate_key": key, "finding_id": item.get("id"), "reason": reason})
            continue
        assert isinstance(key, str)
        if key in existing_by_key:
            path, obj = existing_by_key[key][0]
            skipped_existing.append({
                "candidate_key": key,
                "candidate_id": obj.get("candidate_id"),
                "candidate_ref": str(path.relative_to(root)),
            })
            continue

        candidate = build_candidate(item, ts)
        cid = candidate["candidate_id"]
        path = candidates_dir / f"{cid}.json"
        if path.exists():
            existing = load_json(path, {})
            if existing.get("origin_recon_candidate_key") != key:
                raise ValueError("RECON_CANDIDATE_ID_COLLISION")
            skipped_existing.append({
                "candidate_key": key,
                "candidate_id": existing.get("candidate_id"),
                "candidate_ref": str(path.relative_to(root)),
            })
            existing_by_key[key] = [(path, existing)]
            continue

        save_json(path, candidate)
        existing_by_key[key] = [(path, candidate)]
        created.append({
            "candidate_key": key,
            "candidate_id": cid,
            "candidate_ref": str(path.relative_to(root)),
            "source_count": len(candidate["recon_provenance"]["source_ids"]),
            "queue_status": candidate["queue_status"],
            "scientific_status": candidate["scientific_status"],
        })

    receipt = {
        "schema": "PVA_RECON_CANDIDATE_PROMOTION_V1",
        "run_id": run_id,
        "generated_at": ts,
        "policy": {
            "eligible_states": sorted(ELIGIBLE_RECON_STATES),
            "requires_hunt_gate_pass": True,
            "requires_two_independent_sources": True,
            "initial_queue_status": "NEEDS_DIRECTOR",
            "economic_conclusion": "NO_PROVEN_EDGE",
        },
        "created_count": len(created),
        "skipped_existing_count": len(skipped_existing),
        "ineligible_count": len(ineligible),
        "created": created,
        "skipped_existing": skipped_existing,
        "ineligible": ineligible,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "openai_api": False,
    }
    save_json(receipt_path, receipt)
    return receipt, receipt_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    result, path = promote(args.run_id)
    print(json.dumps({
        "ok": True,
        "created_count": result["created_count"],
        "skipped_existing_count": result["skipped_existing_count"],
        "ineligible_count": result["ineligible_count"],
        "receipt_ref": str(path.relative_to(ROOT)),
        "economic_conclusion": "NO_PROVEN_EDGE",
    }, sort_keys=True))
