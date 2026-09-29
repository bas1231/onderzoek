#!/usr/bin/env python3
"""Install fail-closed OUTBOX -> INFLIGHT semantics in the wake bridge base.

The production wake runtime may be either bridge_server_v2.py itself or the
hardened bridge_server.py wrapper that imports ``bridge_server_v2 as base``.
For the hardened runtime we patch the sibling base module, not the wrapper.
This preserves compaction, heartbeat, task-dedupe and local runtime hardening.

Evidence is never deleted and INFLIGHT is never automatically requeued.
"""

from __future__ import annotations

import argparse
import os
import py_compile
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

MARKER = "# INFLIGHT_RUNTIME_V1"
WRAPPER_IMPORT = "import bridge_server_v2 as base"


def resolve_patch_target(requested: Path) -> tuple[Path, str]:
    """Return the module that owns OUTBOX/ACK semantics and its runtime kind."""
    source = requested.read_text(encoding="utf-8")

    if WRAPPER_IMPORT in source:
        base_target = requested.with_name("bridge_server_v2.py")
        if not base_target.is_file():
            raise SystemExit(
                f"FOUT: hardened wrapper gevonden maar base ontbreekt: {base_target}"
            )
        return base_target, "hardened_wrapper"

    return requested, "direct_base"


def static_inflight_ok(target: Path) -> bool:
    try:
        source = target.read_text(encoding="utf-8")
    except Exception:
        return False
    required = (
        MARKER,
        'INFLIGHT = DATA_DIR / "inflight"',
        "os.replace(path, claimed)",
        "inflight_src if inflight_src.exists() else outbox_src",
    )
    return all(x in source for x in required)


def patch(requested: Path) -> tuple[Path, Path | None, str]:
    target, runtime_kind = resolve_patch_target(requested)
    source = target.read_text(encoding="utf-8")

    if static_inflight_ok(target):
        py_compile.compile(str(target), doraise=True)
        print(f"INFO: inflight runtime patch already present in {target}")
        print(f"RUNTIME_KIND: {runtime_kind}")
        return target, None, runtime_kind

    if MARKER in source:
        raise SystemExit("FOUT: inflight marker aanwezig maar static invariants ontbreken")

    required = [
        'OUTBOX = DATA_DIR / "outbox"\nSENT = DATA_DIR / "sent"',
        'for p in (OUTBOX, SENT, ROUTES):',
        '            _, obj = oldest_event(chat_id, consumer_id)\n            if obj is not None:\n                self.reply_json(200, obj)\n                return',
        '        src = OUTBOX / f"{event_id}.json"\n        dst = SENT / f"{event_id}.json"',
    ]
    missing = [x for x in required if x not in source]
    if missing:
        raise SystemExit(
            f"FOUT: wake base wijkt af; niets gewijzigd; missing_anchors={len(missing)}"
        )

    patched = source.replace(
        'OUTBOX = DATA_DIR / "outbox"\nSENT = DATA_DIR / "sent"',
        'OUTBOX = DATA_DIR / "outbox"\nINFLIGHT = DATA_DIR / "inflight"\nSENT = DATA_DIR / "sent"\n' + MARKER,
        1,
    )
    patched = patched.replace(
        'for p in (OUTBOX, SENT, ROUTES):',
        'for p in (OUTBOX, INFLIGHT, SENT, ROUTES):',
        1,
    )
    patched = patched.replace(
        '            _, obj = oldest_event(chat_id, consumer_id)\n            if obj is not None:\n                self.reply_json(200, obj)\n                return',
        '            path, obj = oldest_event(chat_id, consumer_id)\n'
        '            if obj is not None and path is not None:\n'
        '                # Fail closed: atomically claim before browser delivery.\n'
        '                # Ambiguous delivery remains INFLIGHT and is not retried.\n'
        '                claimed = INFLIGHT / path.name\n'
        '                try:\n'
        '                    os.replace(path, claimed)\n'
        '                except FileNotFoundError:\n'
        '                    continue\n'
        '                self.reply_json(200, obj)\n'
        '                return',
        1,
    )
    patched = patched.replace(
        '        src = OUTBOX / f"{event_id}.json"\n        dst = SENT / f"{event_id}.json"',
        '        inflight_src = INFLIGHT / f"{event_id}.json"\n'
        '        outbox_src = OUTBOX / f"{event_id}.json"\n'
        '        src = inflight_src if inflight_src.exists() else outbox_src\n'
        '        dst = SENT / f"{event_id}.json"',
        1,
    )

    # Informative for a direct-base runtime. Hardened wrappers override /health,
    # so installers must not rely on this flag being externally visible.
    needle = '                "consumer_routing": True,\n'
    if needle in patched and '"inflight_claim": True' not in patched:
        patched = patched.replace(
            needle,
            needle + '                "inflight_claim": True,\n',
            1,
        )

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = target.with_name(target.name + f".bak-inflight-{stamp}")
    shutil.copy2(target, backup)

    fd, tmp_name = tempfile.mkstemp(
        prefix=".bridge-base-inflight-", suffix=".py", dir=str(target.parent)
    )
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        tmp.write_text(patched, encoding="utf-8")
        tmp.chmod(target.stat().st_mode & 0o777 or 0o644)
        py_compile.compile(str(tmp), doraise=True)
        os.replace(tmp, target)
    finally:
        tmp.unlink(missing_ok=True)

    if not static_inflight_ok(target):
        shutil.copy2(backup, target)
        raise SystemExit("FOUT: post-patch static check; base backup restored")

    py_compile.compile(str(target), doraise=True)
    print("PASS: wake base patched for fail-closed inflight claims")
    print("PATCH_TARGET:", target)
    print("RUNTIME_KIND:", runtime_kind)
    print("BACKUP:", backup)
    return target, backup, runtime_kind


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--target",
        default=str(Path.home() / ".local/share/prediction-chat-bridge/bridge_server.py"),
    )
    args = parser.parse_args()
    requested = Path(args.target)
    if not requested.is_file():
        raise SystemExit(f"FOUT: target ontbreekt: {requested}")
    patch(requested)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
