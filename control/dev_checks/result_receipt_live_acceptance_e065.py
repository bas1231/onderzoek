from __future__ import annotations

import json
import time
from pathlib import Path

EVENT_ID = "cont-1791043617262-455c9dc8"
RECEIPT_ID = "RESULT-RECEIPT-cont-1791043617262-455c9dc8"
CONTINUATION_ID = "CONT-a1089bdc6fe1703fb6680694"

TASK_STATE = Path.home() / ".local/state/prediction-command-bus/tasks"
BRIDGE = Path.home() / ".local/share/prediction-chat-bridge"


def load(path: Path):
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def main() -> int:
    deadline = time.time() + 90
    receipt_state = None
    continuation = None
    while time.time() < deadline:
        receipt_state = load(TASK_STATE / f"{RECEIPT_ID}.json")
        continuation = load(BRIDGE / "continuations" / f"{CONTINUATION_ID}.json")
        if (
            receipt_state
            and receipt_state.get("status") == "DISPATCHED"
            and continuation
            and int(continuation.get("last_acked_attempt") or 0) >= 1
        ):
            break
        time.sleep(2)

    sent = (BRIDGE / "sent" / f"{EVENT_ID}.json").is_file()
    inflight = (BRIDGE / "inflight" / f"{EVENT_ID}.json").is_file()
    attempts = int((continuation or {}).get("attempts") or 0)
    acked = int((continuation or {}).get("last_acked_attempt") or 0)
    state = str((continuation or {}).get("state") or "")
    receipt_status = str((receipt_state or {}).get("status") or "")

    ok = (
        receipt_status == "DISPATCHED"
        and acked >= 1
        and attempts == 1
        and sent
        and not inflight
    )
    print(
        "RESULT_RECEIPT_LIVE"
        f"|receipt_status={receipt_status or 'MISSING'}"
        f"|acked_attempt={acked}"
        f"|attempts={attempts}"
        f"|sent={str(sent).lower()}"
        f"|inflight={str(inflight).lower()}"
        f"|continuation_state={state or 'MISSING'}"
    )
    return 0 if ok else 42


if __name__ == "__main__":
    raise SystemExit(main())
