"""Isolated Reddit discovery app. No dependency on the production checkout.

The scoped project executor installs a pinned release under its app-data
allowlist. Only a separate prediction-* user oneshot invokes this script with
ordinary network access. The executor child guard is NEVER bypassed.
No candidate, watchlist, Git, trade, wallet or credential operations occur.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

RELEASE = Path(__file__).resolve().parent
if str(RELEASE) not in sys.path:
    sys.path.insert(0, str(RELEASE))

from control.hourly.recon_engine import discover
from control.reddit_idea_mine import hourly_ingress, source_canary

APP_STATE = Path.home() / ".local/state/prediction-project-executor/apps/reddit_idea_mine"
SCHEMA = "PREDICTION_REDDIT_STANDALONE_RESULT_V1"


def _private_directory(path: Path) -> None:
    if path.exists():
        if not path.is_dir() or path.is_symlink():
            raise ValueError("unsafe application state directory")
    else:
        path.mkdir(parents=True, mode=0o700)
    if path.is_symlink():
        raise ValueError("symlink application state directory")


def _save(root: Path, result: dict) -> Path:
    _private_directory(root)
    output = root / "latest.json"
    if output.is_symlink():
        raise ValueError("unsafe latest result symlink")
    fd, tmp = tempfile.mkstemp(prefix=".reddit-", suffix=".json", dir=str(root))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            os.fchmod(handle.fileno(), 0o600)
            json.dump(result, handle, sort_keys=True, indent=2, ensure_ascii=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, output)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return output


def once(*, probe_only: bool = False, fetch=None, clock: datetime | None = None,
         state: Path | None = None, persist: bool = True) -> dict:
    now = clock or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("aware time required")
    probe = source_canary.probe(fetch=fetch, now=now)
    result = {
        "schema": SCHEMA,
        "timestamp_utc": now.astimezone(timezone.utc).isoformat(),
        "mode": "SOURCE_PROBE" if probe_only else "DISCOVERY_ONESHOT",
        "provider": "arctic_shift",
        "probe": probe,
        "status": "SOURCE_UNVERIFIED",
        "posts_received": 0,
        "leads_accepted": 0,
        "evidence_added": 0,
        "recon_findings": 0,
        "discovery_only": True,
        "candidate_created": False,
        "trade_authorized": False,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "economic_conclusion": "NO_PROVEN_EDGE",
        "errors": [],
        "findings_summary": [],
        "source_evidence": [],
    }
    if probe["status"] == "DATA_OBSERVED":
        result["status"] = "PROBE_PASSED"
        if not probe_only:
            routing = {}
            receipt = hourly_ingress.inject(
                routing, enabled=True, fetch=fetch, now=now
            )
            evidence = routing.get("recon_scout", {}).get("evidence", [])
            findings = discover(routing)
            result.update({
                "status": (
                    "DISCOVERY_PASSED"
                    if receipt["status"] in {"SUCCESS", "PARTIAL"}
                    and int(receipt["evidence_added"]) > 0
                    else "DISCOVERY_NOT_PROVEN"
                ),
                "source_status": receipt["status"],
                "posts_received": int(receipt.get("posts_received") or 0),
                "leads_accepted": int(receipt.get("leads_accepted") or 0),
                "evidence_added": int(receipt.get("evidence_added") or 0),
                "recon_findings": len(findings),
                "errors": receipt.get("errors", [])[:20],
                "findings_summary": [{
                    "id": f.get("id"),
                    "status": f.get("status"),
                    "attack_mode": f.get("attack_mode"),
                    "candidate_key": f.get("candidate_key"),
                } for f in findings[:80]],
                "source_evidence": [{
                    "source_id": x.get("source_id"),
                    "provenance_url": x.get("provenance_url"),
                    "trust_level": "untrusted_external_content",
                    "instruction_authority": False,
                    "snippet_preview": str(x.get("snippet") or "")[:600],
                } for x in evidence[:80]],
            })
    else:
        result["status"] = "SOURCE_UNVERIFIED"
        result["errors"] = [{"error": probe.get("error_type", probe["status"])}]
    if persist:
        result["local_receipt"] = str(_save(state or APP_STATE, result))
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    modes = p.add_mutually_exclusive_group(required=True)
    modes.add_argument("--probe-only", action="store_true")
    modes.add_argument("--once", action="store_true")
    args = p.parse_args()
    result = once(probe_only=args.probe_only)
    # Do not print external Reddit text to the systemd journal.
    compact = {key: result.get(key) for key in (
        "schema", "mode", "status", "posts_received", "leads_accepted",
        "evidence_added", "recon_findings", "errors", "local_receipt",
        "economic_conclusion",
    )}
    compact["probe_status"] = result["probe"]["status"]
    compact["probe_records_seen"] = result["probe"]["records_seen"]
    print("REDDIT_STANDALONE " + json.dumps(compact, sort_keys=True))
    # Source outages are observation results, not systemd installation errors.
    # The separate acceptance task must check the recorded status explicitly.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
