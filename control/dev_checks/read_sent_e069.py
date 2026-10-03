from __future__ import annotations

import json
from pathlib import Path

SENT = Path.home() / ".local/share/prediction-chat-bridge/sent"
EVENTS = [
    ("E066_DIRTY", "1791044341-4ac47ef02246"),
    ("E068_CANONICAL", "1791045027-d0c3709d8671"),
    ("A1089_RECEIPT_ACCEPTANCE", "1791046785-e1fa09a37763"),
]

def load_message(event_id: str) -> str:
    path = SENT / f"{event_id}.json"
    obj = json.loads(path.read_text(encoding="utf-8"))
    return str(obj.get("message") or "").strip()

def main() -> int:
    missing = []
    for label, event_id in EVENTS:
        path = SENT / f"{event_id}.json"
        if not path.is_file():
            missing.append(label)
            print(f"SENT_EVIDENCE|{label}|MISSING")
            continue
        msg = load_message(event_id).replace("\n", " | ")
        print(f"SENT_EVIDENCE|{label}|{msg[:3200]}")
    return 42 if missing else 0

if __name__ == "__main__":
    raise SystemExit(main())
