from __future__ import annotations

import os
from pathlib import Path

import sitecustomize

ROOT = Path.cwd()
PROBE = ROOT / "control/dev_checks/project_guard_fd_canary_e035.tmp"


def main() -> None:
    fd = os.open(PROBE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = -1
            handle.write("PROJECT_GUARD_FD_OK\n")
    finally:
        if fd >= 0:
            os.close(fd)

    if PROBE.read_text(encoding="utf-8") != "PROJECT_GUARD_FD_OK\n":
        raise AssertionError("FD_WRITE_CONTENT_MISMATCH")
    PROBE.unlink()

    read_fd, write_fd = os.pipe()
    try:
        try:
            sitecustomize._check_write_path(write_fd)
        except PermissionError:
            pass
        else:
            raise AssertionError("NON_FILESYSTEM_FD_NOT_BLOCKED")
    finally:
        os.close(read_fd)
        os.close(write_fd)

    print("PROJECT_GUARD_FD_CANARY_PASS")


if __name__ == "__main__":
    main()
