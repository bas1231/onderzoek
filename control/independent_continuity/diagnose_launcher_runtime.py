"""Read-only diagnosis of three existing browser launcher directories.

Never creates directories, reads credentials, changes services, registers
launchers, sends wake events, or starts a ChatGPT session.
"""
from __future__ import annotations

from pathlib import Path

NAMES = ("sent", "routes", "dashboard_launchers")


def diagnose(home: Path) -> tuple[int, str]:
    root = home / ".local/share/prediction-chat-bridge"
    details: list[str] = []
    healthy = True
    for name in NAMES:
        p = root / name
        if p.is_symlink():
            kind = "SYMLINK_REFUSED"
            healthy = False
        elif not p.exists():
            kind = "MISSING"
            healthy = False
        elif not p.is_dir():
            kind = "NOT_DIRECTORY"
            healthy = False
        else:
            count = sum(1 for x in p.iterdir() if x.suffix == ".json"
                        and x.is_file() and not x.is_symlink())
            kind = f"DIR_FILES_{min(count, 9999)}"
        details.append(name + "=" + kind)
    return (0 if healthy else 2), "LAUNCHER_DIR_DIAG=" + ",".join(details)


if __name__ == "__main__":
    try:
        code, message = diagnose(Path.home())
    except OSError as exc:
        code, message = 2, "LAUNCHER_DIR_DIAG=OSERROR_" + type(exc).__name__
    print(message, flush=True)
    raise SystemExit(code)
