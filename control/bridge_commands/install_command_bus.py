#!/usr/bin/env python3
"""Install the read-only GitHub command bus and fail-closed result queue.

The installer never pushes to GitHub and never touches the production repo working
tree. Existing outbox evidence is preserved in quarantine before queue semantics
change from OUTBOX retry to OUTBOX -> INFLIGHT at-most-once delivery.

The active wake runtime may be a hardened wrapper around bridge_server_v2.py.
In that case only the base queue/ACK module is patched; wrapper compaction,
heartbeat, dedupe and browser formatting remain intact.
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
BRIDGE = HOME / ".local/share/prediction-chat-bridge"
BUS = HOME / ".local/share/prediction-command-bus"
BUS_REPO = BUS / "repo"
BUS_CONFIG = HOME / ".config/prediction-command-bus"
BUS_STATE = HOME / ".local/state/prediction-command-bus"
TASK_STATE = BUS_STATE / "tasks"
UNIT_DIR = HOME / ".config/systemd/user"
TOKEN_FILE = HOME / ".config/prediction-chat-bridge/token"
PROD_REPO = HOME / "prediction_research_prod"
WAKE_SERVICE = "prediction-chat-wake.service"
BUS_SERVICE = "prediction-command-bus.service"
BUS_TIMER = "prediction-command-bus.timer"
INFLIGHT_MARKER = "# INFLIGHT_RUNTIME_V1"
WRAPPER_IMPORT = "import bridge_server_v2 as base"


def utc_now() -> str:
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
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass


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


def origin_url() -> str:
    cp = run(["git", "-C", str(PROD_REPO), "remote", "get-url", "origin"], capture=True)
    value = cp.stdout.strip()
    if not value:
        raise RuntimeError("EMPTY_ORIGIN_URL")
    return value


def init_mirror(remote: str) -> str:
    BUS_REPO.mkdir(parents=True, exist_ok=True)
    if not (BUS_REPO / ".git").exists():
        run(["git", "-C", str(BUS_REPO), "init", "-q"])
    run(["git", "-C", str(BUS_REPO), "remote", "remove", "origin"], check=False)
    run(["git", "-C", str(BUS_REPO), "remote", "add", "origin", remote])
    run(["git", "-C", str(BUS_REPO), "fetch", "--quiet", "--depth=1", "origin", "main"])
    return run(["git", "-C", str(BUS_REPO), "rev-parse", "FETCH_HEAD"], capture=True).stdout.strip()


def remote_bytes(path: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(BUS_REPO), "show", f"FETCH_HEAD:{path}"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout


def pin_route(task_id: str) -> dict:
    path = BRIDGE / "routes" / f"{task_id}.json"
    if not path.is_file():
        raise RuntimeError(f"ROUTE_TASK_NOT_FOUND:{task_id}")
    src = json.loads(path.read_text(encoding="utf-8"))
    chat_id = str(src.get("chat_id") or "").strip()
    consumer_id = str(src.get("consumer_id") or "").strip()
    if not chat_id:
        raise RuntimeError("ROUTE_HAS_NO_CHAT_ID")
    route = {
        "schema": "PREDICTION_COMMAND_BUS_ROUTE_V1",
        "source_task_id": task_id,
        "chat_id": chat_id,
        "consumer_id": consumer_id or None,
        "pinned_at_utc": utc_now(),
    }
    atomic_json(BUS_CONFIG / "route.json", route)
    return route


def seed_proof(task_id: str, remote_commit: str) -> None:
    state_path = TASK_STATE / f"{task_id}.json"
    if state_path.exists():
        return
    try:
        raw = remote_bytes(f"control/bridge_commands/inbox/{task_id}.json")
        obj = json.loads(raw.decode("utf-8"))
    except Exception:
        return
    if not isinstance(obj, dict) or obj.get("task_id") != task_id:
        return
    atomic_json(state_path, {
        "schema": "PREDICTION_COMMAND_BUS_TASK_STATE_V1",
        "task_id": task_id,
        "status": "PREEXISTING_PROOF",
        "content_sha256": hashlib.sha256(raw).hexdigest(),
        "remote_commit": remote_commit,
        "recorded_at_utc": utc_now(),
        "reason": "successfully dispatched manually before poller installation",
    })


def archive_outbox(stamp: str) -> tuple[Path, list[dict]]:
    outbox = BRIDGE / "outbox"
    qdir = BRIDGE / "quarantine" / f"pre-inflight-install-{stamp}"
    qdir.mkdir(parents=True, exist_ok=False)
    moved = []
    for src in sorted(outbox.glob("*.json")):
        raw = src.read_bytes()
        rec = {
            "name": src.name,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "mtime_ns": src.stat().st_mtime_ns,
        }
        os.replace(src, qdir / src.name)
        moved.append(rec)
    atomic_json(qdir / "MANIFEST.json", {
        "schema": "PREDICTION_LEGACY_OUTBOX_QUARANTINE_V1",
        "reason": "pre-inflight migration; preserved, not marked sent",
        "created_at_utc": utc_now(),
        "count": len(moved),
        "events": moved,
    })
    return qdir, moved


def restore_outbox(qdir: Path | None) -> None:
    if qdir is None or not qdir.exists():
        return
    outbox = BRIDGE / "outbox"
    outbox.mkdir(parents=True, exist_ok=True)
    for src in qdir.glob("*.json"):
        if src.name == "MANIFEST.json":
            continue
        dst = outbox / src.name
        if not dst.exists():
            os.replace(src, dst)


def runtime_patch_target(active_server: Path) -> tuple[Path, str]:
    source = active_server.read_text(encoding="utf-8")
    if WRAPPER_IMPORT in source:
        base = active_server.with_name("bridge_server_v2.py")
        if not base.is_file():
            raise RuntimeError(f"HARDENED_BASE_MISSING:{base}")
        return base, "hardened_wrapper"
    return active_server, "direct_base"


def inflight_static_ok(path: Path) -> bool:
    try:
        source = path.read_text(encoding="utf-8")
    except Exception:
        return False
    return all(x in source for x in (
        INFLIGHT_MARKER,
        'INFLIGHT = DATA_DIR / "inflight"',
        "os.replace(path, claimed)",
        "inflight_src if inflight_src.exists() else outbox_src",
    ))


def write_units() -> None:
    UNIT_DIR.mkdir(parents=True, exist_ok=True)
    (UNIT_DIR / BUS_SERVICE).write_text(
        "[Unit]\nDescription=Prediction GitHub Command Bus Poller\n"
        "After=network-online.target prediction-chat-router.service\nWants=network-online.target\n\n"
        "[Service]\nType=oneshot\n"
        "ExecStart=/usr/bin/python3 %h/.local/share/prediction-command-bus/command_bus_poller.py --once\n"
        "NoNewPrivileges=true\nPrivateTmp=true\n",
        encoding="utf-8",
    )
    (UNIT_DIR / BUS_TIMER).write_text(
        "[Unit]\nDescription=Prediction GitHub Command Bus Poller Timer\n\n"
        "[Timer]\nOnBootSec=20s\nOnUnitActiveSec=30s\nAccuracySec=2s\nPersistent=true\n"
        "Unit=prediction-command-bus.service\n\n"
        "[Install]\nWantedBy=timers.target\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--route-task", default="BRIDGE-BUS-E001")
    args = parser.parse_args()

    src_dir = Path(__file__).resolve().parent
    poller_src = src_dir / "command_bus_poller.py"
    patch_src = src_dir / "patch_wake_inflight.py"
    if not poller_src.is_file() or not patch_src.is_file():
        raise SystemExit("FOUT: run installer beside poller and inflight patch")

    for p in (
        BUS, BUS_CONFIG, BUS_STATE, TASK_STATE, UNIT_DIR,
        BRIDGE / "outbox", BRIDGE / "sent", BRIDGE / "routes"
    ):
        p.mkdir(parents=True, exist_ok=True)

    if not TOKEN_FILE.is_file():
        raise SystemExit("FOUT: bridge token missing")
    token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not token:
        raise SystemExit("FOUT: bridge token empty")

    health("http://127.0.0.1:8765/health", token)
    health("http://127.0.0.1:8767/health", token)
    if run(
        ["systemctl", "--user", "is-active", "--quiet", "prediction-chat-command.service"],
        check=False,
    ).returncode != 0:
        raise SystemExit("FOUT: prediction-chat-command.service not active")

    py_compile.compile(str(poller_src), doraise=True)
    py_compile.compile(str(patch_src), doraise=True)

    remote_commit = init_mirror(origin_url())
    route = pin_route(args.route_task)
    seed_proof("BRIDGE-BUS-E001", remote_commit)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = BRIDGE / "backups" / f"command-bus-{stamp}"
    backup_dir.mkdir(parents=True, exist_ok=False)
    active_server = BRIDGE / "bridge_server.py"
    if not active_server.is_file():
        raise SystemExit("FOUT: active bridge_server.py missing")

    patch_target, runtime_kind = runtime_patch_target(active_server)
    shutil.copy2(active_server, backup_dir / "bridge_server.py")
    if patch_target != active_server:
        shutil.copy2(patch_target, backup_dir / "bridge_server_v2.py")

    qdir: Path | None = None
    try:
        run(["systemctl", "--user", "stop", WAKE_SERVICE])
        qdir, moved = archive_outbox(stamp)

        patch_run = run(
            [sys.executable, str(patch_src), "--target", str(active_server)],
            capture=True,
        )
        patch_output = patch_run.stdout.strip()
        if not inflight_static_ok(patch_target):
            raise RuntimeError(f"INFLIGHT_STATIC_CHECK_FAILED:{patch_target}")
        py_compile.compile(str(patch_target), doraise=True)
        py_compile.compile(str(active_server), doraise=True)
        (BRIDGE / "inflight").mkdir(parents=True, exist_ok=True)

        shutil.copy2(poller_src, BUS / "command_bus_poller.py")
        (BUS / "command_bus_poller.py").chmod(0o755)
        write_units()
        run(["systemctl", "--user", "daemon-reload"])
        run(["systemctl", "--user", "restart", WAKE_SERVICE])

        wake = health("http://127.0.0.1:8765/health", token)
        if runtime_kind == "hardened_wrapper":
            if wake.get("server_compaction") is not True or wake.get("task_dedupe") is not True:
                raise RuntimeError(f"HARDENED_GUARDRAILS_MISSING:{wake}")
        elif wake.get("inflight_claim") is not True:
            raise RuntimeError(f"DIRECT_BASE_INFLIGHT_HEALTH_MISSING:{wake}")

        test = run(
            [sys.executable, str(BUS / "command_bus_poller.py"), "--once"],
            capture=True,
        ).stdout.strip()
        run(["systemctl", "--user", "enable", "--now", BUS_TIMER])
        if run(
            ["systemctl", "--user", "is-active", "--quiet", BUS_TIMER],
            check=False,
        ).returncode != 0:
            raise RuntimeError("BUS_TIMER_NOT_ACTIVE")

        atomic_json(BUS_STATE / "qualification.json", {
            "schema": "PREDICTION_COMMAND_BUS_QUALIFICATION_V1",
            "task_id": "TIERA-BRIDGE-COMMAND-BUS-20260929-E001",
            "intelligence_tier": "A",
            "implementation_model": "GPT-5.6 Sol",
            "reasoning_level": "UNAVAILABLE_TO_RUNTIME",
            "status": "REQUIRES_HIGH_INTELLIGENCE_REVIEW",
            "installed_at_utc": utc_now(),
            "pinned_route": route,
            "remote_commit": remote_commit,
            "runtime_kind": runtime_kind,
            "inflight_patch_target": str(patch_target),
            "inflight_static_verified": True,
            "wake_health": wake,
            "legacy_outbox_quarantine": str(qdir),
            "legacy_outbox_count": len(moved),
            "poller_self_test": test,
            "patch_output": patch_output,
            "guardrails": {
                "live_trading": False,
                "paid_actions": False,
                "wallet_actions": False,
                "wsl_remote_writes": False,
            },
        })

        print("PASS: command bus installed")
        print("RUNTIME_KIND:", runtime_kind)
        print("INFLIGHT_PATCH_TARGET:", patch_target)
        print("PATCH:", patch_output)
        print("ROUTE:", json.dumps(route, sort_keys=True))
        print("WAKE:", json.dumps(wake, sort_keys=True))
        print("POLLER:", test)
        print("TIMER: active")
        print("LEGACY_OUTBOX_QUARANTINE:", qdir)
        print("STATUS: REQUIRES_HIGH_INTELLIGENCE_REVIEW")
        return 0

    except Exception as exc:
        print(f"FOUT: {type(exc).__name__}: {exc}")
        run(["systemctl", "--user", "disable", "--now", BUS_TIMER], check=False)
        shutil.copy2(backup_dir / "bridge_server.py", active_server)
        base_backup = backup_dir / "bridge_server_v2.py"
        if base_backup.exists():
            shutil.copy2(base_backup, patch_target)
        restore_outbox(qdir)
        run(["systemctl", "--user", "daemon-reload"], check=False)
        run(["systemctl", "--user", "restart", WAKE_SERVICE], check=False)
        print("ROLLBACK: wake runtime/base and outbox restored")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
