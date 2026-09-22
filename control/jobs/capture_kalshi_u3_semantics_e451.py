from __future__ import annotations

import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "knowledge" / "research" / "kalshi_u3_semantics_e451.json"
BASE = "https://api.elections.kalshi.com/trade-api/v2/markets/"
TICKERS = [
    "KXU3-26SEP-T4.0",
    "KXU3-26SEP-T4.1",
    "KXECONSTATU3-26SEP-T4.1",
]

# Deliberately exclude every price/order-book/volume field. This job exists only
# to prove or block contract semantics before any economics are inspected.
ALLOW_FIELDS = {
    "ticker",
    "event_ticker",
    "title",
    "subtitle",
    "yes_sub_title",
    "no_sub_title",
    "rules_primary",
    "rules_secondary",
    "floor_strike",
    "cap_strike",
    "functional_strike",
    "custom_strike",
    "open_time",
    "close_time",
    "expected_expiration_time",
    "expiration_time",
    "latest_expiration_time",
    "occurrence_datetime",
    "early_close_condition",
    "can_close_early",
    "settlement_timer_seconds",
    "is_provisional",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(obj: object) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def fetch_market(ticker: str) -> dict:
    url = BASE + ticker
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "prediction-research-semantic-capture/1.0"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    market = payload.get("market")
    if not isinstance(market, dict):
        raise RuntimeError(f"missing market object for {ticker}")
    if market.get("ticker") != ticker:
        raise RuntimeError(f"ticker mismatch for {ticker}: {market.get('ticker')}")
    return {key: market.get(key) for key in sorted(ALLOW_FIELDS) if key in market}


def main() -> int:
    retrieved_at = now_iso()
    rows: dict[str, dict] = {}
    for ticker in TICKERS:
        semantic = fetch_market(ticker)
        rows[ticker] = {
            "endpoint": BASE + ticker,
            "semantic": semantic,
            "semantic_sha256": stable_hash(semantic),
        }

    artifact = {
        "schema_version": 1,
        "task_id": "KALSHI-U3-SEMANTICS-E451",
        "purpose": "semantic_only_pre_price_payoff_identity_check",
        "retrieved_at": retrieved_at,
        "tickers": rows,
        "price_fields_captured": False,
        "order_book_captured": False,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "economic_conclusion": "NO_PROVEN_EDGE",
        "next_step": "AI/formal review of rules_primary/rules_secondary and strike semantics before any price comparison",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "PASS",
        "artifact": str(OUT.relative_to(ROOT)),
        "tickers": TICKERS,
        "price_fields_captured": False,
        "artifact_sha256": stable_hash(artifact),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
