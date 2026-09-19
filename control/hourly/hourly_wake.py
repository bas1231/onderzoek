from pathlib import Path
from datetime import datetime
import json
import time

def main():
    now = datetime.now().astimezone()
    stamp = now.strftime("%Y%m%dT%H00%z")
    iid = "hourly-research-" + stamp
    idir = Path.home() / ".local/state/prediction-research/incidents"
    idir.mkdir(parents=True, exist_ok=True)
    path = idir / (iid + "__HOURLY_RESEARCH_WAKE.json")
    if path.exists():
        return
    ts = time.time()
    data = {
        "incident_id": iid,
        "task_id": iid,
        "reason": "HOURLY_RESEARCH_WAKE",
        "detail": "Run the hourly autonomous prediction-market research director. Use only free/public sources. Route evidence through specialist agents, falsification, reproduction and publish the hourly report to Git. NO_PROVEN_EDGE is valid. No live trading, paid actions or wallet actions.",
        "status": "OPEN",
        "deliver_to_chat": True,
        "first_seen_at": ts,
        "last_seen_at": ts,
        "automatic_action": "RESEARCH_WAKE_ONLY",
        "running_task_killed": False,
        "paid_action": False,
        "live_trading_action": False,
        "wallet_action": False
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + chr(10))

if __name__ == "__main__":
    main()
