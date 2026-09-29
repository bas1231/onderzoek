#!/usr/bin/env python3
"""Patch the active wake server to atomically claim OUTBOX -> INFLIGHT.

The patch is deliberately narrow so local formatter/status fixes in bridge_server.py
are preserved. It never deletes evidence and it never auto-requeues inflight work.
"""

from __future__ import annotations

import argparse
import py_compile
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

MARKER = "# INFLIGHT_RUNTIME_V1"


def patch(target: Path) -> Path | None:
    source = target.read_text(encoding="utf-8")
    if MARKER in source:
        print("INFO: inflight runtime patch already present")
        return None

    required = [
        'OUTBOX = DATA_DIR / "outbox"\nSENT = DATA_DIR / "sent"',
        'for p in (OUTBOX, SENT, ROUTES):',
        '            _, obj = oldest_event(chat_id, consumer_id)\n            if obj is not None:\n                self.reply_json(200, obj)\n                return',
        '        src = OUTBOX / f"{event_id}.json"\n        dst = SENT / f"{event_id}.json"',
    ]
    missing = [x for x in required if x not in source]
    if missing:
        raise SystemExit("FOUT: active bridge_server.py wijkt af; niets gewijzigd")

    source = source.replace(
        'OUTBOX = DATA_DIR / "outbox"\nSENT = DATA_DIR / "sent"',
        'OUTBOX = DATA_DIR / "outbox"\nINFLIGHT = DATA_DIR / "inflight"\nSENT = DATA_DIR / "sent"\n' + MARKER,
        1,
    )
    source = source.replace(
        'for p in (OUTBOX, SENT, ROUTES):',
        'for p in (OUTBOX, INFLIGHT, SENT, ROUTES):',
        1,
    )
    source = source.replace(
        '            _, obj = oldest_event(chat_id, consumer_id)\n            if obj is not None:\n                self.reply_json(200, obj)\n                return',
        '            path, obj = oldest_event(chat_id, consumer_id)\n'
        '            if obj is not None and path is not None:\n'
        '                # Fail closed: claim exactly once before browser delivery.\n'
        '                # A crash/ambiguous browser result remains INFLIGHT and never\n'
        '                # blocks or auto-replays newer OUTBOX events.\n'
        '                claimed = INFLIGHT / path.name\n'
        '                try:\n'
        '                    os.replace(path, claimed)\n'
        '                except FileNotFoundError:\n'
        '                    continue\n'
        '                self.reply_json(200, obj)\n'
        '                return',
        1,
    )
    source = source.replace(
        '        src = OUTBOX / f"{event_id}.json"\n        dst = SENT / f"{event_id}.json"',
        '        inflight_src = INFLIGHT / f"{event_id}.json"\n'
        '        outbox_src = OUTBOX / f"{event_id}.json"\n'
        '        src = inflight_src if inflight_src.exists() else outbox_src\n'
        '        dst = SENT / f"{event_id}.json"',
        1,
    )

    # Health metadata is informative only; do not fail if a locally patched server
    # has a slightly different health envelope.
    needle = '                "consumer_routing": True,\n'
    if needle in source and '"inflight_claim": True' not in source:
        source = source.replace(needle, needle + '                "inflight_claim": True,\n', 1)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = target.with_name(target.name + f".bak-inflight-{stamp}")
    shutil.copy2(target, backup)

    fd, tmp_name = tempfile.mkstemp(prefix=".bridge-server-inflight-", suffix=".py", dir=str(target.parent))
    Path(tmp_name).write_text(source, encoding="utf-8")
    Path(tmp_name).chmod(0o755)
    py_compile.compile(tmp_name, doraise=True)
    Path(tmp_name).replace(target)

    final = target.read_text(encoding="utf-8")
    checks = {
        "marker": MARKER in final,
        "inflight dir": 'INFLIGHT = DATA_DIR / "inflight"' in final,
        "atomic claim": "os.replace(path, claimed)" in final,
        "ack inflight first": "inflight_src if inflight_src.exists() else outbox_src" in final,
    }
    if not all(checks.values()):
        shutil.copy2(backup, target)
        raise SystemExit("FOUT: post-patch static check; backup restored")

    print("PASS: active wake server patched for fail-closed inflight claims")
    print("BACKUP:", backup)
    return backup


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--target",
        default=str(Path.home() / ".local/share/prediction-chat-bridge/bridge_server.py"),
    )
    args = parser.parse_args()
    target = Path(args.target)
    if not target.is_file():
        raise SystemExit(f"FOUT: target ontbreekt: {target}")
    patch(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
