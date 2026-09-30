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


def sync_python_sources() -> list[str]:
    copied: list[str] = []
    for path in PROD.rglob("*.py"):
        try:
            rel = path.relative_to(PROD)
        except ValueError:
            continue
        parts = set(rel.parts)
        if parts & {".git", ".venv", "__pycache__", "tests"}:
            continue
        if rel.parts[:2] == ("control", "dev_checks"):
            continue
        dst = ROOT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dst)
        copied.append(rel.as_posix())
    if not copied:
        raise AssertionError("NO_LOCAL_PYTHON_SOURCES_SYNCED")
    return sorted(copied)


def main() -> None:
    copied = sync_python_sources()
    mod = load(E039, "e039_for_e043")
    mod.main()
    print("E043_SOURCE_SNAPSHOT_COUNT=" + str(len(copied)))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException as exc:
        tb = traceback.format_exc().splitlines()
        tail = " | ".join(line.strip() for line in tb[-8:] if line.strip())
        raise SystemExit("E043_BUILD_FAIL=" + exc.__class__.__name__ + ":" + " ".join(str(exc).split())[:1600] + " | " + tail[:2200])
