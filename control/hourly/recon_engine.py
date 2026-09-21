from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib
import json

ROOT = Path.cwd()
WATCHLIST = ROOT / "knowledge/recon/watchlist.json"
GRAPH = ROOT / "knowledge/recon/opportunity_graph.json"
OUT = ROOT / "knowledge/runs/recon"

ATTACK_TERMS = {
    "PREDATOR": ["failed", "loss", "losing", "adverse selection", "unprofitable", "market maker"],
    "CLONE_MUTATE": ["profit", "profitable", "strategy", "bot", "return", "roi"],
    "MECHANISM_BREAKER": ["settlement", "fee", "rebate", "collateral", "rule", "oracle", "api", "payout"],
    "HUMAN_WEAKNESS": ["fomo", "overconfidence", "herding", "longshot", "panic", "attention", "bias"],
    "FRONTIER_RAIDER": ["new market", "new product", "release", "changelog", "deprecated", "experimental"],
    "COUNTER_CROWD": ["copycat", "crowded", "crowding", "followers", "herding"],
    "INFORMED_FLOW": ["informed trading", "order flow", "private information", "insider trading"],
}

SPECIALIST = {
    "PREDATOR": ["microstructure", "behavioral"],
    "CLONE_MUTATE": ["microstructure"],
    "MECHANISM_BREAKER": ["settlement", "algebra", "microstructure"],
    "HUMAN_WEAKNESS": ["behavioral"],
    "FRONTIER_RAIDER": ["scout"],
    "COUNTER_CROWD": ["behavioral", "microstructure"],
    "INFORMED_FLOW": ["informed_flow", "microstructure"],
}

def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))

def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)

def fingerprint(source_id: str, attack_mode: str, term: str, snippet: str) -> str:
    raw = "|".join([source_id, attack_mode, term, snippet[:400]]).encode()
    return hashlib.sha256(raw).hexdigest()[:16]

def discover(routing: dict[str, Any]) -> list[dict[str, Any]]:
    docs = []
    seen = set()
    for role_data in routing.values():
        for item in role_data.get("evidence", []):
            key = (item.get("source_id"), item.get("document_sha256"))
            if key in seen:
                continue
            seen.add(key)
            docs.append(item)
    findings = []
    for item in docs:
        text = str(item.get("snippet", ""))
        low = text.lower()
        for mode, terms in ATTACK_TERMS.items():
            term = next((t for t in terms if t in low), None)
            if not term:
                continue
            fid = "RECON-" + fingerprint(str(item.get("source_id")), mode, term, text)
            findings.append({
                "id": fid,
                "observed_at": item.get("retrieved_at"),
                "attack_mode": mode,
                "status": "WATCH",
                "labels": ["RECON_ANOMALY"],
                "claim": "Public evidence contains a Recon-relevant signal; mechanism is unproven.",
                "sources": [{
                    "source_id": item.get("source_id"),
                    "document_sha256": item.get("document_sha256"),
                    "term": term,
                    "point_in_time": item.get("retrieved_at"),
                }],
                "economic_model": {
                    "who_loses": None, "why": None, "who_captures": None,
                    "public_trigger": term, "frequency": None, "capacity": None,
                    "net_after_friction": None, "half_life": None, "crowding": None,
                    "adaptability": None, "kill_condition": None,
                },
                "falsification": {
                    "counterevidence": [],
                    "next_decisive_test": "Establish mechanism, base rate, point-in-time predictiveness and net executable economics.",
                    "required_data": [],
                    "execution_blockers": ["No executable edge established."],
                    "specialist_route": SPECIALIST[mode],
                },
                "snippet": text,
            })
    return findings

def resurrect_if_kill_condition_changed(old: dict[str, Any], fresh: dict[str, Any]) -> bool:
    if old.get("status") != "KILL":
        return False
    old_condition = old.get("economic_model", {}).get("kill_condition")
    new_condition = fresh.get("economic_model", {}).get("kill_condition")
    return bool(old_condition and new_condition is not None and old_condition != new_condition)

def update_watchlist(findings: list[dict[str, Any]]) -> dict[str, Any]:
    watch = load_json(WATCHLIST, {"version": 1, "items": []})
    old = {x["id"]: x for x in watch.get("items", [])}
    added = 0
    changed = 0
    for f in findings:
        if f["id"] not in old:
            old[f["id"]] = f
            added += 1
        else:
            prev = old[f["id"]]
            if resurrect_if_kill_condition_changed(prev, f):
                prev["status"] = "WATCH"
                labels = set(prev.get("labels", []))
                labels.add("EDGE_RESURRECTION")
                prev["labels"] = sorted(labels)
                prev["resurrection_reason"] = "Stored kill condition changed; candidate requires fresh falsification."
                changed += 1
            if prev.get("sources") != f.get("sources"):
                prev["sources"] = f["sources"]
                prev["last_observed_at"] = f.get("observed_at")
                changed += 1
    watch["items"] = sorted(old.values(), key=lambda x: x["id"])
    watch["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_json(WATCHLIST, watch)
    return {"added": added, "changed": changed, "total": len(watch["items"])}

def update_graph(findings: list[dict[str, Any]]) -> dict[str, Any]:
    graph = load_json(GRAPH, {"version": 1, "nodes": [], "edges": []})
    nodes = {x["id"]: x for x in graph.get("nodes", [])}
    edges = {(x["from"], x["to"], x["type"]): x for x in graph.get("edges", [])}
    for f in findings:
        nodes[f["id"]] = {"id": f["id"], "type": "recon_finding", "status": f["status"]}
        for role in f["falsification"]["specialist_route"]:
            rid = "role:" + role
            nodes[rid] = {"id": rid, "type": "specialist"}
            edges[(f["id"], rid, "route_to")] = {"from": f["id"], "to": rid, "type": "route_to"}
    graph["nodes"] = sorted(nodes.values(), key=lambda x: x["id"])
    graph["edges"] = sorted(edges.values(), key=lambda x: (x["from"], x["to"], x["type"]))
    graph["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_json(GRAPH, graph)
    return {"nodes": len(graph["nodes"]), "edges": len(graph["edges"])}

def run(run_id: str, routing_path: Path) -> tuple[dict[str, Any], Path]:
    routing = load_json(routing_path, {})
    findings = discover(routing)
    watch = update_watchlist(findings)
    graph = update_graph(findings)
    counts = {s: sum(1 for f in findings if f["status"] == s) for s in ["KILL","WATCH","HUNT","PROVE"]}
    result = {
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "objects_checked": sum(len(v.get("evidence", [])) for v in routing.values()),
        "findings": findings,
        "state_counts": counts,
        "watchlist": watch,
        "opportunity_graph": graph,
        "economic_conclusion": "NO_PROVEN_EDGE",
        "live_trading": False, "paid_actions": False, "wallet_actions": False,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / (run_id + ".json")
    save_json(path, result)
    return result, path
