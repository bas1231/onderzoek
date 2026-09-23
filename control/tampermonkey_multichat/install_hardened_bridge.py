#!/usr/bin/env python3
"""Install hardened 8765 delivery server and dedicated nightshift userscript.

Designed for the allowlisted DEV_TASK runner: no shell, no systemctl, no generic
process killing, no external network. systemd's existing Restart=always policy
brings the exact service back after SIGTERM.
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


def fail(msg: str) -> None:
    raise RuntimeError(msg)


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
    shutil.copy2(HARDENED_SOURCE, TARGET)
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
        if (
            last.get("ok") is True
            and last.get("server_compaction") is True
            and last.get("task_dedupe") is True
            and last.get("nightshift_userscript") is True
            and int(last.get("max_browser_message") or 0) <= 900
            and script_ok
        ):
            print("HARDENED_BRIDGE=PASS")
            print("SERVER_COMPACTION=1")
            print("TASK_DEDUPE=1")
            print("NIGHTSHIFT_USERSCRIPT=1")
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
