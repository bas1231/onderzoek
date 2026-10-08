"""Turn approved Reddit discovery leads into the existing Recon discovery evidence contract.
No watchlist mutation, source fetching or candidate promotion happens here.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

from control.hourly.recon_engine import discover


def to_recon_routing(batch: dict) -> dict:
    if batch.get("schema") != "PREDICTION_REDDIT_DISCOVERY_BATCH_V1":
        raise ValueError("wrong batch schema")
    evidence = []
    for lead in batch.get("leads", []):
        if (lead.get("schema") != "PREDICTION_REDDIT_DISCOVERY_LEAD_V1"
            or lead.get("status") != "DISCOVERY_ONLY_UNVERIFIED"
            or lead.get("economic_status") != "NO_PROVEN_EDGE"):
            raise ValueError("unverified lead guard invalid")
        if not lead.get("discovery_relevant"):
            continue
        snippet = " ".join([
            lead.get("title", ""), lead.get("body", ""),
            *lead.get("counterarguments", [])[:10],
        ])[:10000]
        evidence.append({
            "source_id": "reddit_thread:" + lead["lead_id"],
            "document_sha256": hashlib.sha256(snippet.encode()).hexdigest(),
            "retrieved_at": lead["created_at_utc"],
            "snippet": snippet,
            "provenance_url": lead["url"],
            "discovery_only": True,
        })
    return {"recon_scout": {"evidence": evidence}}


def preview(batch: dict) -> dict:
    routing = to_recon_routing(batch)
    findings = discover(routing)
    return {
        "schema": "PREDICTION_REDDIT_RECON_PREVIEW_V1",
        "evidence_count": len(routing["recon_scout"]["evidence"]),
        "findings": findings,
        "watchlist_written": False,
        "candidate_created": False,
        "scientific_status": "NO_PROVEN_EDGE",
    }


def main() -> None:
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--batch",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--routing-output",type=Path,default=None)
    a=p.parse_args()
    batch=json.loads(a.batch.read_text(encoding="utf-8"))
    result=preview(batch)
    if a.routing_output is not None:
        routing=to_recon_routing(batch)
        a.routing_output.write_text(json.dumps(routing,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"evidence_count":result["evidence_count"],"finding_count":len(result["findings"])}))


if __name__=="__main__":
    main()
