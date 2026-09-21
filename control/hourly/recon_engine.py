from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib
import json
import re

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

# Single generic words are discovery hints, not enough by themselves for WATCH.
WEAK_TERMS = {"loss", "bot", "api", "release", "attention", "return", "rule", "strategy", "profit", "fee"}
ECONOMIC_CONTEXT = {
    "market", "trading", "trader", "order", "orderbook", "price", "spread", "liquidity",
    "maker", "taker", "settlement", "payout", "contract", "rebate", "collateral",
    "oracle", "position", "fill", "volume", "probability", "prediction", "arbitrage",
    "adverse selection", "longshot", "fomo", "herding", "crowding", "roi",
}
BOILERPLATE_PHRASES = {
    "privacy policy", "web policy", "foia", "accessibility statement", "usa.gov",
    "sitemap", "sign in", "search public comments", "submit tips", "headquarters",
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

def _term_present(text: str, term: str) -> bool:
    if " " in term:
        return term in text
    return re.search(r"(?<![a-z0-9_])" + re.escape(term) + r"(?![a-z0-9_])", text) is not None

def _all_hits(text: str) -> list[tuple[str, str]]:
    hits = []
    for mode, terms in ATTACK_TERMS.items():
        for term in terms:
            if _term_present(text, term):
                hits.append((mode, term))
    return hits

def _economic_context_count(text: str) -> int:
    return sum(1 for term in ECONOMIC_CONTEXT if _term_present(text, term))

def _boilerplate_ratio(text: str) -> float:
    words = re.findall(r"[a-z0-9]+", text)
    if not words:
        return 1.0
    matched = 0
    for phrase in BOILERPLATE_PHRASES:
        if phrase in text:
            matched += len(phrase.split())
    return min(1.0, matched / max(1, len(words)))

def _quality(text: str, hits: list[tuple[str, str]]) -> dict[str, Any]:
    unique_terms = {term for _, term in hits}
    strong_terms = {term for term in unique_terms if term not in WEAK_TERMS}
    context_count = _economic_context_count(text)
    boilerplate_ratio = _boilerplate_ratio(text)
    # WATCH requires either a strong Recon term plus market context, or corroborating
    # weak terms plus market context. Generic navigation/footer matches stay DISCOVER.
    watch = (
        boilerplate_ratio < 0.08
        and context_count >= 2
        and (bool(strong_terms) or len(unique_terms) >= 2)
    )
    return {
        "status": "WATCH" if watch else "DISCOVER",
        "economic_context_count": context_count,
        "matched_terms": sorted(unique_terms),
        "strong_terms": sorted(strong_terms),
        "boilerplate_ratio": round(boilerplate_ratio, 4),
    }

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
        hits = _all_hits(low)
        if not hits:
            continue
        quality = _quality(low, hits)
        # Keep DISCOVER/noise in the run for auditability, but do not persist it
        # into the Watchlist or Opportunity Graph.
        for mode in ATTACK_TERMS:
            mode_terms = [term for hit_mode, term in hits if hit_mode == mode]
            if not mode_terms:
                continue
            term = mode_terms[0]
            fid = "RECON-" + fingerprint(str(item.get("source_id")), mode, term, text)
            findings.append({
                "id": fid,
                "observed_at": item.get("retrieved_at"),
                "attack_mode": mode,
                "status": quality["status"],
                "labels": ["RECON_ANOMALY"] if quality["status"] == "WATCH" else ["RECON_DISCOVERY_NOISE"],
                "claim": (
                    "Public evidence contains a context-supported Recon signal; mechanism is unproven."
                    if quality["status"] == "WATCH"
                    else "Keyword signal retained for audit only; insufficient economic context for WATCH."
                ),
                "quality": quality,
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
        if f.get("status") == "DISCOVER":
            continue
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
        if f.get("status") == "DISCOVER":
            continue
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
    counts = {s: sum(1 for f in findings if f["status"] == s) for s in ["DISCOVER","KILL","WATCH","HUNT","PROVE"]}
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
