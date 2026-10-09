"""Read-only one-shot verification of 2026-10-09 session rollback.

This is temporary verification code. Checks only two independent sidecar runtime
source copies and the independent continuity timer; no bridge/executor paths.
"""
from __future__ import annotations
from pathlib import Path
import hashlib
import subprocess


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    home = Path.home()
    repo = Path(__file__).resolve().parents[2]
    runtime = home / ".local/share/prediction-project-executor/independent-continuity"
    for name in ("observer.py", "coordinator.py"):
        expected = repo / "control/independent_continuity" / name
        actual = runtime / name
        if not actual.is_file() or actual.is_symlink() or sha(expected) != sha(actual):
            print("ROLLBACK_VERIFY_FAIL: " + name + " mismatch", flush=True)
            return 3
        print("ROLLBACK_HASH_PASS=" + name, flush=True)
    for unit, property_, expected in (
        ("prediction-independent-continuity.timer", "ActiveState", "inactive"),
        ("prediction-independent-continuity.timer", "UnitFileState", "disabled"),
        ("prediction-independent-continuity.service", "ActiveState", "inactive"),
    ):
        cp = subprocess.run(["systemctl", "--user", "show", unit, "-p", property_, "--value"],
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            timeout=20, check=False)
        state = cp.stdout.strip()
        if cp.returncode or state != expected:
            print(f"ROLLBACK_VERIFY_FAIL: {unit} {property_}={state[:80]}", flush=True)
            return 4
        print(f"ROLLBACK_UNIT_PASS={unit}:{property_}={expected}", flush=True)
    print("ROLLBACK_VERIFIED=1", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
