from __future__ import annotations

import importlib.util
import traceback
from pathlib import Path

ROOT = Path.cwd()
E031 = ROOT / "control/dev_checks/autobuild_build_e031_runner.py"
E034 = ROOT / "control/dev_checks/autobuild_build_e034_runner.py"
PROD = Path.home() / "prediction_research_prod"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def filesystem_context() -> list[str]:
    out: set[str] = set()
    for relroot in ("tests", "control/codex_supervisor"):
        root = PROD / relroot
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(PROD)
            if "__pycache__" in rel.parts or path.suffix in {".pyc", ".pyo"}:
                continue
            out.add(rel.as_posix())
    return sorted(out)


def main() -> None:
    e031 = load(E031, "e031_for_e039")
    e034 = load(E034, "e034_for_e039")
    base = e031.load_base()
    context = filesystem_context()
    if not context:
        raise AssertionError("NO_LOCAL_TEST_CONTROL_CONTEXT")

    def no_prod_git(*args: str) -> list[str]:
        # E028.prepare only uses git_prod for local-context discovery. Replace
        # those reads with the already computed read-only filesystem snapshot.
        if not args or args[0] != "ls-files":
            raise AssertionError("UNEXPECTED_PROD_GIT_REQUEST:" + repr(args))
        if "--others" in args:
            return []
        return context

    base.git_prod = no_prod_git
    base.run_pytest = e034.guarded_pytest
    e031.load_base = lambda: base
    e031.main()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException as exc:
        tb = traceback.format_exc().splitlines()
        tail = " | ".join(line.strip() for line in tb[-8:] if line.strip())
        raise SystemExit("E039_BUILD_FAIL=" + exc.__class__.__name__ + ":" + " ".join(str(exc).split())[:1600] + " | " + tail[:2200])
