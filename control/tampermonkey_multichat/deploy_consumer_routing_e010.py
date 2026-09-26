#!/usr/bin/env python3
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
DATA = HOME / '.local/share/prediction-chat-bridge'
TOKEN_FILE = HOME / '.config/prediction-chat-bridge/token'
BASE_SOURCE = HERE / 'bridge_server_v2.py'
ROUTER_SOURCE = HERE / 'command_router.py'
BASE_TARGET = DATA / 'bridge_server_v2.py'
WAKE_TARGET = DATA / 'bridge_server.py'
ROUTER_TARGET = DATA / 'command_router.py'
BACKUP_DIR = DATA / 'backups' / f'consumer_routing_{int(time.time())}'


def fail(msg: str) -> None:
    raise RuntimeError(msg)


def matching_pids(fragment: Path, port: str) -> list[int]:
    matches: list[int] = []
    expected = str(fragment)
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            raw = (proc / 'cmdline').read_bytes()
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        parts = [p.decode('utf-8', errors='replace') for p in raw.split(b'\0') if p]
        joined = ' '.join(parts)
        if expected in joined and '--port' in parts and port in parts:
            matches.append(int(proc.name))
    return matches


def health(port: int, token: str) -> dict:
    req = Request(
        f'http://127.0.0.1:{port}/health',
        headers={'Authorization': f'Bearer {token}'},
    )
    with urlopen(req, timeout=2) as resp:
        return json.loads(resp.read(8192) or b'{}')


def patch_installed_wake_health(text: str) -> str:
    if '"consumer_routing": True' in text:
        return text
    needle = '                "multichat": True,\n                "server_compaction": True,'
    replacement = '                "multichat": True,\n                "consumer_routing": True,\n                "server_compaction": True,'
    if text.count(needle) != 1:
        fail('installed wake health patch point not unique')
    return text.replace(needle, replacement, 1)


def restart_by_signal(target: Path, port: str) -> int:
    pids = matching_pids(target, port)
    if len(pids) != 1:
        fail(f'expected one process for {port}, found {len(pids)}')
    old = pids[0]
    os.kill(old, signal.SIGTERM)
    return old


def wait_green(token: str, old_wake: int, old_router: int) -> tuple[dict, dict]:
    deadline = time.monotonic() + 15.0
    last_wake: dict = {}
    last_router: dict = {}
    while time.monotonic() < deadline:
        time.sleep(0.25)
        try:
            wake_pids = matching_pids(WAKE_TARGET, '8765')
            router_pids = matching_pids(ROUTER_TARGET, '8767')
            if len(wake_pids) != 1 or len(router_pids) != 1:
                continue
            if wake_pids[0] == old_wake or router_pids[0] == old_router:
                continue
            last_wake = health(8765, token)
            last_router = health(8767, token)
            if (
                last_wake.get('ok') is True
                and last_wake.get('consumer_routing') is True
                and last_wake.get('server_compaction') is True
                and last_router.get('ok') is True
                and last_router.get('consumer_routing') is True
                and int(last_router.get('version') or 0) >= 2
            ):
                return last_wake, last_router
        except Exception:
            continue
    fail(f'health did not become green: wake={last_wake} router={last_router}')


def restore_and_restart(backups: dict[Path, Path]) -> None:
    for target, backup in backups.items():
        if backup.exists():
            shutil.copy2(backup, target)
    for target, port in ((WAKE_TARGET, '8765'), (ROUTER_TARGET, '8767')):
        for pid in matching_pids(target, port):
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass


def main() -> int:
    required = (BASE_SOURCE, ROUTER_SOURCE, BASE_TARGET, WAKE_TARGET, ROUTER_TARGET, TOKEN_FILE)
    if not all(path.is_file() for path in required):
        fail('required source/runtime file missing')
    token = TOKEN_FILE.read_text(encoding='utf-8').strip()
    if not token:
        fail('token empty')

    base_text = BASE_SOURCE.read_text(encoding='utf-8')
    router_text = ROUTER_SOURCE.read_text(encoding='utf-8')
    compile(base_text, str(BASE_SOURCE), 'exec')
    compile(router_text, str(ROUTER_SOURCE), 'exec')
    if 'route_binding_for_task' not in base_text or 'consumer_route_mismatch' not in base_text:
        fail('base source lacks consumer enforcement')
    if 'consumer_routing' not in router_text or 'consumer_id' not in router_text:
        fail('router source lacks consumer persistence')

    wake_text = WAKE_TARGET.read_text(encoding='utf-8')
    # Preserve all existing hardened/dead-man runtime changes; only add the new
    # health capability flag to the installed wrapper.
    if 'server_compaction' not in wake_text or 'heartbeat_retry_nonce' not in wake_text:
        fail('installed hardened wake invariants missing')
    patched_wake = patch_installed_wake_health(wake_text)
    compile(patched_wake, str(WAKE_TARGET), 'exec')

    BACKUP_DIR.mkdir(parents=True, exist_ok=False)
    backups: dict[Path, Path] = {}
    for target in (BASE_TARGET, WAKE_TARGET, ROUTER_TARGET):
        backup = BACKUP_DIR / target.name
        shutil.copy2(target, backup)
        backups[target] = backup

    old_wake = old_router = -1
    try:
        shutil.copy2(BASE_SOURCE, BASE_TARGET)
        shutil.copy2(ROUTER_SOURCE, ROUTER_TARGET)
        WAKE_TARGET.write_text(patched_wake, encoding='utf-8')
        os.chmod(BASE_TARGET, 0o644)
        os.chmod(ROUTER_TARGET, 0o755)
        os.chmod(WAKE_TARGET, 0o755)

        old_wake = restart_by_signal(WAKE_TARGET, '8765')
        old_router = restart_by_signal(ROUTER_TARGET, '8767')
        wake_health, router_health = wait_green(token, old_wake, old_router)
    except Exception:
        restore_and_restart(backups)
        raise

    print('CONSUMER_ROUTING_DEPLOY=PASS')
    print('WAKE_CONSUMER_ROUTING=' + str(wake_health.get('consumer_routing')).lower())
    print('ROUTER_CONSUMER_ROUTING=' + str(router_health.get('consumer_routing')).lower())
    print('ROUTER_VERSION=' + str(router_health.get('version')))
    print('BACKUP_DIR=' + str(BACKUP_DIR))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
