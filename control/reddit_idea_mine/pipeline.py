"""Run an offline Reddit discussion discovery batch through the existing Recon workflow.

Writes are scoped to a caller-selected root. Never fetches network data and never
promotes any candidate from this adapter.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import patch

from control.reddit_idea_mine.ingest import ingest
from control.reddit_idea_mine.recon_handoff import to_recon_routing
from control.hourly import recon_engine


def run(input_path: Path, root: Path, run_id: str) -> dict:
    if not run_id or not all(c.isalnum() or c in "-_" for c in run_id) or len(run_id) > 90:
        raise ValueError("invalid run id")
    if not root.is_dir():
        raise ValueError("output root must exist")
    records = json.loads(input_path.read_text(encoding="utf-8"))
    batch = ingest(records)
    output = root / "knowledge/runs/reddit_idea_mine"
    output.mkdir(parents=True, exist_ok=True)
    routing_path = output / (run_id + "-routing.json")
    batch_path = output / (run_id + "-leads.json")
    receipt_path = output / (run_id + "-receipt.json")
    if any(p.exists() or p.is_symlink() for p in (routing_path, batch_path, receipt_path)):
        raise FileExistsError("immutable run already exists")
    routing = to_recon_routing(batch)
    batch_path.write_text(json.dumps(batch, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    routing_path.write_text(json.dumps(routing, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    # Reuse the existing Recon discovery/persistence logic, rather than forge
    # HUNT status, create candidates or bypass its independent-source gate.
    with (
        patch.object(recon_engine, "ROOT", root),
        patch.object(recon_engine, "WATCHLIST", root / "knowledge/recon/watchlist.json"),
        patch.object(recon_engine, "GRAPH", root / "knowledge/recon/opportunity_graph.json"),
        patch.object(recon_engine, "OUT", root / "knowledge/runs/recon"),
        patch.object(recon_engine, "HUNT_PLANS", root / "knowledge/runs/recon_hunts"),
    ):
        recon, recon_path = recon_engine.run(run_id, routing_path)
    receipt = {
        "schema": "PREDICTION_REDDIT_IDEA_MINE_RUN_V1",
        "run_id": run_id,
        "inputs": batch["counts"],
        "recon_findings": len(recon["findings"]),
        "recon_ref": str(recon_path.relative_to(root)),
        "leads_ref": str(batch_path.relative_to(root)),
        "routing_ref": str(routing_path.relative_to(root)),
        "candidate_promotions": 0,
        "status": "DISCOVERY_ONLY",
        "economic_status": "NO_PROVEN_EDGE",
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.input, args.root, args.run_id), sort_keys=True))


if __name__ == "__main__":
    main()
