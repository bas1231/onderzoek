#!/usr/bin/env python3
"""Install the Prediction GitHub command bus and fail-closed result queue.

This installer intentionally does not touch the production repository working tree
and never performs a Git push. Existing OUTBOX evidence is preserved in quarantine
before the queue semantic change is activated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import py_compile
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

HOME = Path.home()
BRIDGE = HOME / ".local" / "share" / "prediction-chat-bridge"
BUS = HOME / ".local" / "share" / "prediction-command-bus"
BUS_REPO = BUS / "repo"
BUS_CONFIG = HOME / ".config" / "prediction-command-bus"
BUS_STATE = HOME / ".local" / "state" / "prediction-command-bus"
TASK_STATE = BUS_STATE / "tasks"
UNIT_DIR = HOME / ".config" / "systemd" / "user"
TOKEN_FILE = HOME / ".config" / "prediction-chat-bridge" / "token"
PROD_REPO = HOME / "prediction_research_prod"
WAKE_SERVICE = "prediction-chat-wake.service"
ROUTER_SERVICE = "prediction-chat-router.service"
BUS_SERVICE = "prediction-command-bus.service"
BUS_TIMER = "prediction-command-bus.timer"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run(cmd: list[str], *, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def atomic_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def health(url: str, token: str, attempts: int = 30) -> dict:
    last = None
    for _ in range(attempts):
        try:
            req = Request(url, headers={"Authorization": f"Bearer {token}"})
            with urlopen(req, timeout=2) as resp:
                obj = json.loads(resp.read().decode("utf-8"))
            if isinstance(obj, dict) and obj.get("ok") is True:
                return obj
            last = obj
        except Exception as exc:
            last = f"{type(exc).__name__}:{exc}"
        time.sleep(0.25)
    raise RuntimeError(f"HEALTH_FAILED:{url}:{last}")


def git_remote_url() -> str:
    cp = run(["git", "-C", str(PROD_REPO), "remote", "get-url", "origin"], capture=True)
    value = cp.stdout.strip()
    if not value:
        raise RuntimeError("EMPTY_ORIGIN_URL")
    return value


def init_bus_repo(remote_url: str) -> None:
    BUS_REPO.mkdir(parents=True, exist_ok=True)
    if not (BUS_REPO / ".git").exists():
        run(["git", "-C", str(BUS_REPO), "init", "-q"])
    run(["git", "-C", str(BUS_REPO), "remote", "remove", "origin"], check=False)
    run(["git", "-C", str(BUS_REPO), "remote", "add", "origin", remote_url])
    run(["git", "-C", str(BUS_REPO), "fetch", "--quiet", "--depth=1", "origin", "main"])


def remote_bytes(path: str) -> bytes:
    cp = subprocess.run(
        ["git", "-C", str(BUS_REPO), "show", f"FETCH_HEAD:{path}"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return cp.stdout


def seed_proof_task(task_id: str) -> None:
    path = f"control/bridge_commands/inbox/{task_id}.json"
    try:
        raw = remote_bytes(path)
    except subprocess.CalledProcessError:
        return
    try:
        obj = json.loads(raw.decode("utf-8"))
    except Exception:
        return
    if not isinstance(obj, dict) or obj.get("task_id") != task_id:
        return
    state_path = TASK_STATE / f"{task_id}.json"
    if state_path.exists():
        return
    remote_commit = run(["git", "-C", str(BUS_REPO), "rev-parse", "FETCH_HEAD"], capture=True).stdout.strip()
    atomic_json(state_path, {
        "schema": "PREDICTION_COMMAND_BUS_TASK_STATE_V1",
        "task_id": task_id,
        "status": "PREEXISTING_PROOF",
        "content_sha256": hashlib.sha256(raw).hexdigest(),
        "remote_commit": remote_commit,
        "recorded_at_utc": now_utc(),
        "reason": "successfully dispatched manually before poller installation",
    })


def pin_route(route_task: str) -> dict:
    source = BRIDGE / "routes" / f"{route_task}.json"
    if not source.is_file():
        raise RuntimeError(f"ROUTE_TASK_NOT_FOUND:{route_task}")
    route = json.loads(source.read_text(encoding="utf-8"))
    chat_id = str(route.get("chat_id") or "").strip()
    consumer_id = str(route.get("consumer_id") or "").strip()
    if not chat_id:
        raise RuntimeError("ROUTE_HAS_NO_CHAT_ID")
    pinned = {
        "schema": "PREDICTION_COMMAND_BUS_ROUTE_V1",
        "source_task_id": route_task,
        "chat_id": chat_id,
        "consumer_id": consumer_id or None,
        "pinned_at_utc": now_utc(),
    }
    atomic_json(BUS_CONFIG / "route.json", pinned)
    return pinned


def archive_legacy_outbox(stamp: str) -> tuple[Path, list[dict]]:
    outbox = BRIDGE / "outbox"
    quarantine = BRIDGE / "quarantine" / f"pre-inflight-install-{stamp}"
    quarantine.mkdir(parents=True, exist_ok=False)
    moved = []
    for path in sorted(outbox.glob("*.json")):
        record = {
            "name": path.name,
            "sha256": sha256_file(path),
            "mtime_ns": path.stat().st_mtime_ns,
        }
        dst = quarantine / path.name
        os.replace(path, dst)
        moved.append(record)
    manifest = {
        "schema": "PREDICTION_LEGACY_OUTBOX_QUARANTINE_V1",
        "reason": "pre-inflight migration; preserved, not marked sent",
        "created_at_utc": now_utc(),
        "count": len(moved),
        "events": moved,
    }
    atomic_json(quarantine / "MANIFEST.json", manifest)
    return quarantine, moved


def restore_quarantine(quarantine: Path) -> None:
    outbox = BRIDGE / "outbox"
    outbox.mkdir(parents=True, exist_ok=True)
    if not quarantine.exists():
        return
    for path in quarantine.glob("*.json"):
        if path.name == "MANIFEST.json":
            continue
        dst = outbox / path.name
        if not dst.exists():
            os.replace(path, dst)


def write_units() -> None:
    UNIT_DIR.mkdir(parents=True, exist_ok=True)
    (UNIT_DIR / BUS_SERVICE).write_text(
        """[Unit]\nDescription=Prediction GitHub Command Bus Poller\nAfter=network-online.target prediction-chat-router.service\nWants=network-online.target\n\n[Service]\nType=oneshot\nExecStart=/usr/bin/python3 %h/.local/share/prediction-command-bus/command_bus_poller.py --once\nNoNewPrivileges=true\nPrivateTmp=true\n\n""",
        encoding="utf-8",
    )
    (UNIT_DIR / BUS_TIMER).write_text(
        """[Unit]\nDescription=Prediction GitHub Command Bus Poller Timer\n\n[Timer]\nOnBootSec=20s\nOnUnitActiveSec=30s\nAccuracySec=2s\nPersistent=true\nUnit=prediction-command-bus.service\n\n[Install]\nWantedBy=timers.target\n""",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--route-task", default="BRIDGE-BUS-E001")
    args = parser.parse_args()

    source_dir = Path(__file__).resolve().parent
    poller_src = source_dir / "command_bus_poller.py"
    patch_src = source_dir / "patch_wake_inflight.py"
    if not poller_src.is_file() or not patch_src.is_file():
        raise SystemExit("FOUT: installer must run beside command_bus_poller.py and patch_wake_inflight.py")

    for p in (BUS, BUS_CONFIG, BUS_STATE, TASK_STATE, UNIT_DIR, BRIDGE / "outbox", BRIDGE / "sent", BRIDGE / "routes"):
        p.mkdir(parents=True, exist_ok=True)

    token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not token:
        raise SystemExit("FOUT: bridge token missing")

    # Preflight: do not mutate anything unless the three local services are reachable.
    health("http://127.0.0.1:8765/health", token)
    health("http://127.0.0.1:8767/health", token)
    if run(["systemctl", "--user", "is-active", "--quiet", "prediction-chat-command.service"], check=False).returncode != 0:
        raise SystemExit("FOUT: prediction-chat-command.service is not active")

    py_compile.compile(str(poller_src), doraise=True)
    py_compile.compile(str(patch_src), doraise=True)

    remote_url = git_remote_url()
    init_bus_repo(remote_url)
    pinned = pin_route(args.route_task)
    seed_proof_task("BRIDGE-BUS-E001")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = BRIDGE / "backups" / f"command-bus-{stamp}"
    backup_dir.mkdir(parents=True, exist_ok=False)
    active_server = BRIDGE / "bridge_server.py"
    if not active_server.is_file():
        raise SystemExit("FOUT: active bridge_server.py missing")
    shutil.copy2(active_server, backup_dir / "bridge_server.py")
    for unit_name in (BUS_SERVICE, BUS_TIMER):
        unit = UNIT_DIR / unit_name
        if unit.exists():
            shutil.copy2(unit, backup_dir / unit_name)

    quarantine = None
    try:
        run(["systemctl", "--user", "stop", WAKE_SERVICE])
        quarantine, moved = archive_legacy_outbox(stamp)

        run([sys.executable, str(patch_src), "--target", str(active_server)])
        (BRIDGE / "inflight").mkdir(parents=True, exist_ok=True)

        shutil.copy2(poller_src, BUS / "command_bus_poller.py")
        (BUS / "command_bus_poller.py").chmod(0o755)
        write_units()

        run(["systemctl", "--user", "daemon-reload"])
        run(["systemctl", "--user", "restart", WAKE_SERVICE])
        wake_health = health("http://127.0.0.1:8765/health", token)
        if wake_health.get("inflight_claim") is not True:
            raise RuntimeError(f"WAKE_INFLIGHT_HEALTH_MISSING:{wake_health}")

        # Deterministic dry execution against the real read-only mirror. The proof
        # task is already seeded and therefore cannot be re-dispatched.
        cp = run([sys.executable, str(BUS / "command_bus_poller.py"), "--once"], capture=True)
        poll_result = cp.stdout.strip()

        run(["systemctl", "--user", "enable", "--now", BUS_TIMER])
        if run(["systemctl", "--user", "is-active", "--quiet", BUS_TIMER], check=False).returncode != 0:
            raise RuntimeError("BUS_TIMER_NOT_ACTIVE")

        qualification = {
            "schema": "PREDICTION_COMMAND_BUS_QUALIFICATION_V1",
            "task_id": "TIERA-BRIDGE-COMMAND-BUS-20260929-E001",
            "intelligence_tier": "A",
            "implementation_model": "GPT-5.6 Sol",
            "reasoning_level": "UNAVAILABLE_TO_RUNTIME",
            "status": "REQUIRES_HIGH_INTELLIGENCE_REVIEW",
            "installed_at_utc": now_utc(),
            "pinned_route": pinned,
            "legacy_outbox_quarantine": str(quarantine),
            "legacy_outbox_count": len(moved),
            "poller_self_test": poll_result,
            "guardrails": {
                "live_trading": false,
                "paid_actions": false,
                "wallet_actions": false,
                "wsl_remote_writes": false
            }
        }
        # JSON booleans above are intentionally represented below in Python.
        qualification["guardrails"] = {
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "wsl_remote_writes": False,
        }
        atomic_json(BUS_STATE / "qualification.json", qualification)

        print("PASS: command bus installed")
        print("ROUTE:", json.dumps(pinned, sort_keys=True))
        print("WAKE:", json.dumps(wake_health, sort_keys=True))
        print("POLLER:", poll_result)
        print("TIMER: active")
        print("LEGACY_OUTBOX_QUARANTINE:", quarantine)
        print("STATUS: REQUIRES_HIGH_INTELLIGENCE_REVIEW")
        return 0

    except Exception as exc:
        print(f"FOUT: {type(exc).__name__}: {exc}")
        run(["systemctl", "--user", "disable", "--now", BUS_TIMER], check=False)
        shutil.copy2(backup_dir / "bridge_server.py", active_server)
        if quarantine is not None:
            restore_quarantine(quarantine)
        run(["systemctl", "--user", "daemon-reload"], check=False)
        run(["systemctl", "--user", "restart", WAKE_SERVICE], check=False)
        print("ROLLBACK: active wake server and legacy outbox restored")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
