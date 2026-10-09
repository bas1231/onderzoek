"""Read-only verification of an installed standalone Reddit one-shot receipt."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

STATE = Path.home() / ".local/state/prediction-project-executor/apps/reddit_idea_mine/latest.json"


def check(mode: str, path: Path = STATE) -> dict:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"status": "MISSING_OR_INVALID_RECEIPT"}
    result = {
        "status": "NOT_PROVEN",
        "mode": mode,
        "observed_mode": doc.get("mode"),
        "observed_status": doc.get("status"),
        "source_status": doc.get("source_status"),
        "probe_status": (doc.get("probe") or {}).get("status"),
        "posts_received": doc.get("posts_received", 0),
        "evidence_added": doc.get("evidence_added", 0),
        "recon_findings": doc.get("recon_findings", 0),
        "live_trading": doc.get("live_trading"),
        "economic_conclusion": doc.get("economic_conclusion"),
    }
    safe = (doc.get("schema") == "PREDICTION_REDDIT_STANDALONE_RESULT_V1"
            and doc.get("live_trading") is False
            and doc.get("paid_actions") is False
            and doc.get("wallet_actions") is False
            and doc.get("candidate_created") is False
            and doc.get("economic_conclusion") == "NO_PROVEN_EDGE")
    if safe and (doc.get("probe") or {}).get("status") == "DATA_OBSERVED":
        if mode == "probe" and doc.get("mode") == "SOURCE_PROBE" and doc.get("status") == "PROBE_PASSED":
            result["status"] = "PROBE_VERIFIED"
        if (mode == "discovery" and doc.get("mode") == "DISCOVERY_ONESHOT"
            and doc.get("status") == "DISCOVERY_PASSED"
            and doc.get("source_status") in ("SUCCESS", "PARTIAL")
            and doc.get("evidence_added", 0) > 0
            and doc.get("recon_findings", 0) > 0):
            result["status"] = "DISCOVERY_VERIFIED"
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("probe", "discovery"), required=True)
    args = parser.parse_args()
    r = check(args.mode)
    print("REDDIT_ACCEPTANCE " + json.dumps(r, sort_keys=True))
    return 0 if r["status"] in ("PROBE_VERIFIED", "DISCOVERY_VERIFIED") else 12


if __name__ == "__main__":
    raise SystemExit(main())
