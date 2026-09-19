from pathlib import Path
from datetime import datetime
import json

ROOT = Path(__file__).resolve().parents[2]
AGENTS = ROOT / "agents/registry.json"
SOURCES = ROOT / "knowledge/sources/registry.json"

def create_manifest(now=None):
    now = now or datetime.now().astimezone()
    run_id = "hourly-" + now.strftime("%Y%m%dT%H0000%z")
    agents = json.loads(AGENTS.read_text())
    sources = json.loads(SOURCES.read_text())
    data = {
        "run_id": run_id,
        "started_at": now.isoformat(),
        "status": "STARTED",
        "candidate_status": "UNPROVEN",
        "decision": "NO_PROVEN_EDGE",
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "agents": {r["id"]: "PENDING" for r in agents["roles"]},
        "sources": {s["id"]: "PENDING" for s in sources["sources"]},
        "gates": {
            "source_provenance": "PENDING",
            "point_in_time": "PENDING",
            "signal_edge": "PENDING",
            "market_edge": "PENDING",
            "execution_reality": "PENDING",
            "falsification": "PENDING",
            "reproduction": "PENDING"
        }
    }
    out = ROOT / "knowledge/runs" / (run_id + ".json")
    out.parent.mkdir(parents=True, exist_ok=True)
    if not out.exists():
        out.write_text(json.dumps(data, indent=2, sort_keys=True) + chr(10))
    return out, data

if __name__ == "__main__":
    path, data = create_manifest()
    print(json.dumps({"ok": True, "run_id": data["run_id"], "path": str(path.relative_to(ROOT))}, sort_keys=True))
