from __future__ import annotations

import importlib.util
import shutil
import traceback
from pathlib import Path

ROOT = Path.cwd()
PROD = Path.home() / "prediction_research_prod"
E039 = ROOT / "control/dev_checks/autobuild_build_e039_runner.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def copy_named_sources() -> list[str]:
    copied: list[str] = []
    wanted = {"executor_preflight.py", "browser_bridge.py", "git_local_only.py"}
    for path in PROD.rglob("*.py"):
        try:
            rel = path.relative_to(PROD)
        except ValueError:
            continue
        if any(part in {".git", ".venv", "__pycache__"} for part in rel.parts):
            continue
        if path.name not in wanted:
            continue
        dst = ROOT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dst)
        copied.append(rel.as_posix())
    missing = wanted - {Path(x).name for x in copied}
    if missing:
        raise AssertionError("LOCAL_SAFETY_SOURCE_MISSING:" + repr(sorted(missing)))
    return sorted(copied)


def main() -> None:
    copied = copy_named_sources()
    mod = load(E039, "e039_for_e042")
    mod.main()
    print("E042_LOCAL_SAFETY_SOURCES=" + repr(copied))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException as exc:
        tb = traceback.format_exc().splitlines()
        tail = " | ".join(line.strip() for line in tb[-8:] if line.strip())
        raise SystemExit("E042_BUILD_FAIL=" + exc.__class__.__name__ + ":" + " ".join(str(exc).split())[:1600] + " | " + tail[:2200])
