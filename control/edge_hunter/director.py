from pathlib import Path
import json
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
LANE_REGISTRY = ROOT / "control/edge_hunter/lane_registry.json"

def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def prepare(run_id):
    run_path = ROOT / "knowledge/runs" / (run_id + ".json")
    routing_path = ROOT / "knowledge/runs" / (run_id + "-routing.json")
    run = load_json(run_path)
    routing = load_json(routing_path) if routing_path.exists() else {}
    registry = load_json(LANE_REGISTRY)
    packet = {
        "edge_hunter_version": 1,
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "system_objective": "Continuously discover and falsify execution-realistic prediction-market edges across all lanes.",
        "weather_is_one_lane": True,
        "decision": "NO_PROVEN_EDGE",
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "lanes": {}
    }
    for lane, spec in registry["lanes"].items():
        evidence = []
        gaps = []
        for role in spec["evidence_roles"]:
            role_row = routing.get(role, {})
            evidence.extend(role_row.get("evidence", []))
            gaps.extend(role_row.get("coverage_gaps", []))
        packet["lanes"][lane] = {
            "objective": spec["objective"],
            "primary_tests": spec["primary_tests"],
            "evidence_count": len(evidence),
            "coverage_gaps": sorted(set(gaps)),
            "candidate_status": "UNPROVEN",
            "next_action": "SEMANTIC_REVIEW_AND_FALSIFICATION"
        }
    out = ROOT / "knowledge/runs/edge_hunter" / ("edge-hunt-" + run_id + ".json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out

if __name__ == "__main__":
    import sys
    print(prepare(sys.argv[1]))
