from __future__ import annotations

from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "control/hourly/systemd"
USER_UNIT_DIR = Path.home() / ".config/systemd/user"
UNITS = (
    "prediction-runtime-sync.service",
    "prediction-runtime-sync.timer",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def install(*, dry_run: bool = False) -> dict[str, object]:
    sources = [SOURCE_DIR / name for name in UNITS]
    missing = [str(path) for path in sources if not path.exists()]
    if missing:
        raise FileNotFoundError("missing runtime-sync unit(s): " + ", ".join(missing))

    plan = [
        {
            "unit": source.name,
            "source": str(source),
            "destination": str(USER_UNIT_DIR / source.name),
            "sha256": sha256(source),
        }
        for source in sources
    ]

    if dry_run:
        return {
            "ok": True,
            "status": "DRY_RUN",
            "plan": plan,
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
        }

    USER_UNIT_DIR.mkdir(parents=True, exist_ok=True)
    for source in sources:
        destination = USER_UNIT_DIR / source.name
        tmp = destination.with_suffix(destination.suffix + ".tmp")
        shutil.copyfile(source, tmp)
        tmp.replace(destination)

    commands = (
        ["systemctl", "--user", "daemon-reload"],
        ["systemctl", "--user", "enable", "--now", "prediction-runtime-sync.timer"],
    )
    for command in commands:
        proc = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()[-2000:]
            raise RuntimeError(f"{' '.join(command)} failed: {detail}")

    return {
        "ok": True,
        "status": "INSTALLED",
        "plan": plan,
        "timer": "prediction-runtime-sync.timer",
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = install(dry_run=args.dry_run)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
