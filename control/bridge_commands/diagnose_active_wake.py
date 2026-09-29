#!/usr/bin/env python3
"""Read-only diagnostic for the active Prediction wake bridge.

Prints only structural information needed to safely adapt the inflight patch.
It never writes files, restarts services, reads the bridge token, or mutates Git.
"""
from __future__ import annotations

import hashlib
import py_compile
import re
from pathlib import Path

P = Path.home() / ".local/share/prediction-chat-bridge/bridge_server.py"

if not P.is_file():
    raise SystemExit(f"FOUT: active server ontbreekt: {P}")

raw = P.read_bytes()
s = raw.decode("utf-8")
lines = s.splitlines()

print("=== ACTIVE WAKE DIAGNOSTIC V1 ===")
print("PATH:", P)
print("SHA256:", hashlib.sha256(raw).hexdigest())
print("BYTES:", len(raw))
try:
    py_compile.compile(str(P), doraise=True)
    print("PY_COMPILE: PASS")
except Exception as exc:
    print("PY_COMPILE: FAIL", type(exc).__name__, str(exc))

markers = [
    "# INFLIGHT_RUNTIME_V1",
    "# bridge_ping_status_mapping_v1",
    'OUTBOX = DATA_DIR / "outbox"',
    'INFLIGHT = DATA_DIR / "inflight"',
    'SENT = DATA_DIR / "sent"',
    "def ensure_dirs",
    "def oldest_event",
    "def do_GET",
    "def do_POST",
    "os.replace(path, claimed)",
    "inflight_src if inflight_src.exists() else outbox_src",
]
print("\n=== MARKERS ===")
for m in markers:
    print(("YES" if m in s else "NO "), repr(m))

patterns = [
    r"OUTBOX\s*=.*",
    r"INFLIGHT\s*=.*",
    r"SENT\s*=.*",
    r"for p in .*OUTBOX.*",
    r"oldest_event\(chat_id,\s*consumer_id\)",
    r"src\s*=.*OUTBOX.*event_id.*",
    r"dst\s*=.*SENT.*event_id.*",
    r"inflight_claim",
]
print("\n=== MATCHING LINES ===")
for i, line in enumerate(lines, 1):
    if any(re.search(pat, line) for pat in patterns):
        print(f"{i}: {line}")


def show_context(label: str, needle: str, before: int = 8, after: int = 18) -> None:
    print(f"\n=== {label} ===")
    hits = [i for i, line in enumerate(lines) if needle in line]
    if not hits:
        print("NOT_FOUND:", needle)
        return
    for n, idx in enumerate(hits[:3], 1):
        lo = max(0, idx - before)
        hi = min(len(lines), idx + after + 1)
        print(f"--- hit {n} line {idx+1} ---")
        for j in range(lo, hi):
            print(f"{j+1}: {lines[j]}")

show_context("CONSTANTS", 'OUTBOX = DATA_DIR / "outbox"', 5, 12)
show_context("ENSURE_DIRS", "def ensure_dirs", 2, 16)
show_context("NEXT CLAIM AREA", "oldest_event(chat_id, consumer_id)", 12, 24)
show_context("ACK SOURCE AREA", 'src = OUTBOX / f"{event_id}.json"', 12, 30)
show_context("HEALTH AREA", '"consumer_routing"', 10, 14)

print("\n=== RECENT SERVER BACKUPS ===")
for q in sorted(P.parent.glob("bridge_server.py.bak*"), key=lambda x: x.stat().st_mtime_ns)[-8:]:
    print(q.name, q.stat().st_size)

print("\nDIAGNOSE_KLAAR")
