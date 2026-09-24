from __future__ import annotations

from pathlib import Path
import importlib.util
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def load_hourly_cycle():
    path = ROOT / "control/hourly/hourly_cycle.py"
    spec = importlib.util.spec_from_file_location("prediction_hourly_cycle", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load hourly cycle from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.modules.pop(spec.name, None)
        raise
    return mod


def latest_canonical_run_id() -> str:
    """Return the newest canonical hourly manifest, never a derivative JSON file."""
    candidates = []
    for path in (ROOT / "knowledge/runs").glob("hourly-*.json"):
        stem = path.stem
        # Canonical run IDs have no derivative suffix after the UTC offset.
        # Validate by requiring the manifest itself to name the same run_id.
        try:
            import json
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("run_id") == stem and data.get("status") is not None:
            candidates.append(path)
    if not candidates:
        raise RuntimeError("no canonical hourly run manifest found")
    newest = max(candidates, key=lambda p: p.stat().st_mtime)
    return newest.stem


def run_required_checkpoint(script: str, label: str, timeout: int = 180) -> None:
    proc = subprocess.run(
        [str(ROOT / ".venv/bin/python"), str(ROOT / script)],
        check=False,
        timeout=timeout,
        cwd=str(ROOT),
    )
    print(label, proc.returncode)
    if proc.returncode != 0:
        raise RuntimeError(f"{label} failed with rc={proc.returncode}")


def main() -> int:
    # Do not use runpy(..., run_name='__main__') here. hourly_cycle.py ends in
    # SystemExit(main()), which used to terminate this wrapper with rc=0 before
    # Edge Hunter and durable checkpoints ever ran.
    hourly = load_hourly_cycle()
    cycle_rc = int(hourly.main())
    if cycle_rc == 75:
        # Expected work-cadence cooldown. The systemd unit declares 75 a
        # successful no-work outcome, so cooldown is visible without looking
        # like a scheduler failure.
        print("HOURLY_CYCLE_COOLDOWN")
        return 75
    if cycle_rc != 0:
        raise RuntimeError(f"hourly cycle failed with rc={cycle_rc}")

    run_id = latest_canonical_run_id()
    sys.path.insert(0, str(ROOT / "control/edge_hunter"))
    from director import prepare

    packet = prepare(run_id)
    print("EDGE_HUNTER_PACKET", packet)

    # These checkpoints are part of the scheduled cycle. A failure must be
    # observable to systemd rather than being printed and silently converted
    # into a successful scheduler run.
    run_required_checkpoint(
        "control/jobs/hourly_asset_fill_checkpoint_e354.py",
        "ASSET_FILL_CHECKPOINT_RC",
    )
    run_required_checkpoint(
        "control/jobs/hourly_kwi_full_station_checkpoint_e371.py",
        "KWI_FULL_STATION_CHECKPOINT_RC",
    )
    run_required_checkpoint(
        "control/hourly/git_checkpoint.py",
        "GIT_CHECKPOINT_RC",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
