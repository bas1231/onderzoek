import json
from pathlib import Path

POLICY = Path(__file__).parent / "policy.json"

BLOCKED_PATTERNS = [
    "order",
    "trade",
    "buy",
    "sell",
    "withdraw",
    "deposit",
    "wallet",
    "private_key",
    "api_payment",
    "send",
    "transfer",
    "crypto",
    "fund",
    "payment",
    "payout",
    "subscribe",
    "subscription",
    "purchase",
    "checkout",
    "invoice",
    "billing",
    "credit_card",
    "card",
    "license",
    "upgrade",
    "premium"
]

def check_action(action):
    action = action.lower().replace("-", "_")

    try:
        policy = json.loads(POLICY.read_text())
        if not isinstance(policy, dict) or policy.get("mode") != "research_only":
            raise ValueError("research-only policy required")
        permissions = policy.get("permissions")
        if not isinstance(permissions, dict) or any(permissions.get(key) is not False for key in ("place_orders", "wallet_access", "crypto_transfer", "live_trading", "paid_api_calls", "external_write")):
            raise ValueError("unsafe policy permissions")
        configured = policy.get("blocked_actions")
        if not isinstance(configured, list) or not all(isinstance(x, str) and x for x in configured):
            raise ValueError("invalid blocked_actions")
    except (OSError, ValueError, TypeError):
        return {"status": "BLOCKED_BY_POLICY", "reason": "policy unavailable, malformed or unsafe"}

    blocked = configured + BLOCKED_PATTERNS

    for item in blocked:
        item = item.lower().replace("-", "_")
        if item in action or item.replace("_","") in action.replace("_",""):
            return {
                "status": "BLOCKED_BY_POLICY",
                "reason": f"{action} matches blocked action {item}"
            }

    return {
        "status": "ALLOWED",
        "reason": "research action permitted"
    }


if __name__ == "__main__":
    tests = [
        "place_order",
        "kalshi_buy",
        "withdraw_wallet",
        "send_crypto",
        "transfer_funds",
        "api_payment",
        "subscribe_service",
        "purchase_api_credits",
        "credit_card_payment",
        "write_report"
    ]

    for t in tests:
        print(f"{t:25} -> {check_action(t)}")
