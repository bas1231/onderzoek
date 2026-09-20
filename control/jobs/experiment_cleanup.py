from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

STATE_ROOT = Path.home() / ".local/state/prediction-research"
CLEANUP_STATE = STATE_ROOT / "cleanup"

TERMINAL_STATES = {
    "COMPLETED",
    "FAILED",
    "ABORTED",
    "FALSIFIED",
    "TESTED_NEGATIVE",
}

# Deze permanente control-plane resources mogen NOOIT door
# experiment-cleanup worden verwijderd.
PROTECTED_UNITS = {
    "prediction-research-browser-bridge.service",
    "prediction-research-executor.service",
    "prediction-research-lifecycle-supervisor.service",
    "prediction-research-hourly-director.service",
    "prediction-research-hourly-director.timer",
    "prediction-research-kalshi-weather-index-recorder.service",
    "prediction-research-kalshi-weather-index-recorder.timer",
    "prediction-research-twc-recorder.service",
    "prediction-research-twc-recorder.timer",
}

# Alleen scratch/runtime onder deze roots mag automatisch weg.
ALLOWED_DELETE_ROOTS = (
    STATE_ROOT / "experiments",
    Path.home() / ".cache/prediction-research/experiments",
    Path("/tmp/prediction-research-experiments"),
)


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            print(file=handle)
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(tmp, path)

    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def inside_allowed_root(path: Path) -> bool:
    resolved = path.expanduser().resolve(strict=False)

    for root in ALLOWED_DELETE_ROOTS:
        allowed = root.expanduser().resolve(strict=False)

        try:
            resolved.relative_to(allowed)
            return resolved != allowed
        except ValueError:
            pass

    return False


def validate_manifest(manifest: dict) -> tuple[bool, str]:
    experiment_id = str(manifest.get("experiment_id") or "").strip()

    if not experiment_id:
        return False, "missing experiment_id"

    state = str(manifest.get("state") or "").upper()

    if state not in TERMINAL_STATES:
        return False, f"non-terminal state {state!r}"

    cleanup = manifest.get("cleanup")

    if not isinstance(cleanup, dict):
        return False, "no explicit cleanup object"

    if cleanup.get("enabled") is not True:
        return False, "cleanup not explicitly enabled"

    for unit in cleanup.get("systemd_user_units", []):
        if unit in PROTECTED_UNITS:
            return False, f"protected unit requested: {unit}"

        if not (
            unit.startswith("prediction-research-exp-")
            or unit.startswith("prediction-experiment-")
        ):
            return False, f"unit lacks experiment ownership prefix: {unit}"

    for raw_path in cleanup.get("delete_paths", []):
        path = Path(raw_path).expanduser()

        if not inside_allowed_root(path):
            return False, f"delete path outside scratch allowlist: {path}"

    return True, "ok"


def run_systemctl(*args: str) -> dict:
    proc = subprocess.run(
        ["systemctl", "--user", *args],
        text=True,
        capture_output=True,
        check=False,
    )

    return {
        "command": ["systemctl", "--user", *args],
        "returncode": proc.returncode,
        "stdout": proc.stdout[-2000:],
        "stderr": proc.stderr[-2000:],
    }


def cleanup_manifest(path: Path, dry_run: bool = False) -> dict:
    try:
        manifest = json.loads(path.read_text())
    except Exception as exc:
        return {
            "status": "REFUSED",
            "manifest": str(path),
            "reason": f"invalid JSON: {exc}",
        }

    ok, reason = validate_manifest(manifest)

    if not ok:
        return {
            "status": "REFUSED",
            "manifest": str(path),
            "experiment_id": manifest.get("experiment_id"),
            "reason": reason,
        }

    experiment_id = str(manifest["experiment_id"])
    cleanup = manifest["cleanup"]

    receipt_path = CLEANUP_STATE / f"{experiment_id}.json"

    # Idempotent: succesvolle cleanup nooit tweemaal uitvoeren.
    if receipt_path.exists():
        try:
            previous = json.loads(receipt_path.read_text())
            if previous.get("status") == "CLEANED":
                return {
                    "status": "ALREADY_CLEANED",
                    "experiment_id": experiment_id,
                    "receipt": str(receipt_path),
                }
        except Exception:
            pass

    actions = []

    for unit in cleanup.get("systemd_user_units", []):
        if dry_run:
            actions.append({
                "type": "systemd",
                "unit": unit,
                "action": "would_disable_now",
            })
            continue

        actions.append(run_systemctl("disable", "--now", unit))

        unit_path = Path.home() / ".config/systemd/user" / unit

        if unit_path.exists():
            unit_path.unlink()
            actions.append({
                "type": "delete_unit_file",
                "path": str(unit_path),
            })

    if cleanup.get("systemd_user_units") and not dry_run:
        actions.append(run_systemctl("daemon-reload"))

    for raw_path in cleanup.get("delete_paths", []):
        target = Path(raw_path).expanduser()

        if dry_run:
            actions.append({
                "type": "delete_path",
                "path": str(target),
                "action": "would_delete",
            })
            continue

        if target.is_symlink() or target.is_file():
            target.unlink(missing_ok=True)
        elif target.is_dir():
            shutil.rmtree(target)

        actions.append({
            "type": "delete_path",
            "path": str(target),
            "action": "deleted",
        })

    result = {
        "status": "DRY_RUN" if dry_run else "CLEANED",
        "experiment_id": experiment_id,
        "terminal_state": manifest["state"],
        "manifest": str(path),
        "cleaned_at": time.time(),
        "actions": actions,
        "evidence_preserved": True,
        "paid_action": False,
        "live_trading_action": False,
        "wallet_action": False,
    }

    if not dry_run:
        atomic_json(receipt_path, result)

    return result


def scan(manifest_dir: Path, dry_run: bool = False) -> list[dict]:
    if not manifest_dir.exists():
        return []

    results = []

    for path in sorted(manifest_dir.glob("*.json")):
        result = cleanup_manifest(path, dry_run=dry_run)

        if result["status"] != "REFUSED":
            results.append(result)

    return results
