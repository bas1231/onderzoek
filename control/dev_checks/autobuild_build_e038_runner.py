from __future__ import annotations

import importlib.util
import traceback
from pathlib import Path

ROOT = Path.cwd()
E037 = ROOT / "control/dev_checks/autobuild_build_e037_runner.py"


def load_e037():
    spec = importlib.util.spec_from_file_location("e037", E037)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    try:
        load_e037().main()
    except BaseException as exc:
        lines = [line.strip() for line in traceback.format_exc().splitlines() if line.strip()]
        tail = " | ".join(lines[-12:])
        raise SystemExit(f"E038_BUILD_FAIL={type(exc).__name__}:{exc} | {tail}"[:6000])


if __name__ == "__main__":
    main()
