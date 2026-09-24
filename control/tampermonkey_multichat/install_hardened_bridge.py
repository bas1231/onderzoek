#!/usr/bin/env python3
"""Install hardened 8765 delivery server and dedicated nightshift userscript.

Designed for the allowlisted DEV_TASK runner: no shell, no systemctl, no generic
process killing, no external network. systemd's existing Restart=always policy
brings the exact service back after SIGTERM.

The installer also applies the fast dead-man continuation hardening to the
installed server so a reinstall cannot silently restore the old 600-second
fallback. The canonical source remains separately reviewable; the installed
runtime must expose explicit health flags proving the hardening is active.
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import time
from pathlib import Path
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent
HOME = Path.home()
DATA = HOME / ".local" / "share" / "prediction-chat-bridge"
TOKEN_FILE = HOME / ".config" / "prediction-chat-bridge" / "token"
TARGET = DATA / "bridge_server.py"
BASE_TARGET = DATA / "bridge_server_v2.py"
NIGHTSHIFT_TARGET = DATA / "prediction-nightshift-wake.user.js"
HARDENED_SOURCE = HERE / "bridge_server_hardened.py"
BASE_SOURCE = HERE / "bridge_server_v2.py"
NIGHTSHIFT_SOURCE = HERE / "prediction-nightshift-wake.user.js"
BACKUP = DATA / "bridge_server.pre_hardened.py"
EXPECTED_FRAGMENT = str(TARGET)
EXPECTED_PORT = "8765"
FAST_DEADMAN_SECONDS = 15.0


def fail(msg: str) -> None:
    raise RuntimeError(msg)


def replace_once(text: str, old: str, new: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        fail(f"fast_deadman_patch_fragment_count_{count}: {old[:80]}")
    return text.replace(old, new, 1)


def fast_deadman_runtime_source(text: str) -> str:
    """Return hardened server text with 15s continuation dead-man semantics."""
    text = replace_once(
        text,
        "Only ten full minutes without either kind of activity produce a wake message.",
        "Only fifteen seconds without either kind of activity produce a wake message.",
    )
    text = replace_once(
        text,
        "DEFAULT_HEARTBEAT_INTERVAL = 600.0",
        "DEFAULT_HEARTBEAT_INTERVAL = 15.0",
    )
    text = replace_once(
        text,
        '''HEARTBEAT_MESSAGE = (\n    "ga door. Als de afgesproken nightshift-taak volledig is afgerond, "\n    "negeer deze heartbeat en start niets nieuws."\n)''',
        '''def heartbeat_message(token: str) -> str:\n    return (\n        "ga door. Als de afgesproken nightshift-taak volledig is afgerond, "\n        "negeer deze heartbeat en start niets nieuws. "\n        "Als een nieuwe WSL-uitvoering nodig is: gebruik ALTIJD een NIEUWE "\n        "task_id/execution-id; herhaal nooit een eerder gebruikte task_id. "\n        f"Continuation nonce: {token}."\n    )''',
    )
    text = replace_once(
        text,
        "return min(600.0, max(15.0, value))",
        "return min(DEFAULT_HEARTBEAT_INTERVAL, max(15.0, value))",
    )
    text = replace_once(
        text,
        '"message": HEARTBEAT_MESSAGE,',
        '"message": heartbeat_message(token),',
    )
    text = replace_once(
        text,
        '"heartbeat_inactivity_reset": True,',
        '"heartbeat_inactivity_reset": True,\n                "heartbeat_retry_nonce": True,\n                "heartbeat_fresh_task_id_required": True,',
    )
    return text


def matching_pids() -> list[int]:
    matches: list[int] = []
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            raw = (proc / "cmdline").read_bytes()
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        parts = [p.decode("utf-8", errors="replace") for p in raw.split(b"\0") if p]
        joined = " ".join(parts)
        if EXPECTED_FRAGMENT in joined and "--port" in parts and EXPECTED_PORT in parts:
            matches.append(int(proc.name))
    return matches


def health(token: str) -> dict:
    req = Request(
        "http://127.0.0.1:8765/health",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urlopen(req, timeout=2) as resp:
        return json.loads(resp.read(8192) or b"{}")


def userscript_ok() -> bool:
    with urlopen("http://127.0.0.1:8765/prediction-nightshift-wake.user.js", timeout=2) as resp:
        body = resp.read(65536).decode("utf-8", errors="replace")
    return (
        resp.status == 200
        and "@name         Prediction Nightshift Wake" in body
        and "@version      0.3." in body
        and "NIGHTSHIFT_WSL_RESULT_V1" in body
    )


def main() -> int:
    sources = (HARDENED_SOURCE, BASE_SOURCE, NIGHTSHIFT_SOURCE)
    if not all(path.is_file() for path in sources):
        fail("source_missing")
    if not TOKEN_FILE.is_file():
        fail("token_missing")
    token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not token:
        fail("token_empty")

    pids = matching_pids()
    if len(pids) != 1:
        fail(f"expected_exactly_one_8765_bridge_process_found_{len(pids)}")

    DATA.mkdir(parents=True, exist_ok=True)
    if TARGET.exists():
        shutil.copy2(TARGET, BACKUP)
    shutil.copy2(BASE_SOURCE, BASE_TARGET)
    hardened_text = HARDENED_SOURCE.read_text(encoding="utf-8")
    TARGET.write_text(fast_deadman_runtime_source(hardened_text), encoding="utf-8")
    shutil.copy2(NIGHTSHIFT_SOURCE, NIGHTSHIFT_TARGET)
    os.chmod(TARGET, 0o755)
    os.chmod(BASE_TARGET, 0o644)
    os.chmod(NIGHTSHIFT_TARGET, 0o644)

    os.kill(pids[0], signal.SIGTERM)

    deadline = time.monotonic() + 12.0
    last = None
    while time.monotonic() < deadline:
        time.sleep(0.35)
        try:
            last = health(token)
            script_ok = userscript_ok()
        except Exception:
            continue
        interval = last.get("heartbeat_interval_seconds")
        interval_ok = interval is None or float(interval) <= FAST_DEADMAN_SECONDS
        if (
            last.get("ok") is True
            and last.get("server_compaction") is True
            and last.get("task_dedupe") is True
            and last.get("server_heartbeat") is True
            and last.get("nightshift_userscript") is True
            and last.get("heartbeat_retry_nonce") is True
            and last.get("heartbeat_fresh_task_id_required") is True
            and interval_ok
            and int(last.get("max_browser_message") or 0) <= 900
            and script_ok
        ):
            print("HARDENED_BRIDGE=PASS")
            print("SERVER_COMPACTION=1")
            print("TASK_DEDUPE=1")
            print("SERVER_HEARTBEAT=1")
            print("NIGHTSHIFT_USERSCRIPT=1")
            print("HEARTBEAT_FAST_DEADMAN=1")
            print("HEARTBEAT_RETRY_NONCE=1")
            print("HEARTBEAT_FRESH_TASK_ID_REQUIRED=1")
            print("MAX_BROWSER_MESSAGE=900")
            return 0

    if BACKUP.exists():
        shutil.copy2(BACKUP, TARGET)
    print("HARDENED_BRIDGE=FAIL")
    if isinstance(last, dict):
        print(f"HEALTH_VERSION={last.get('version', 'UNKNOWN')}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
