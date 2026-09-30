from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

ROOT = Path.cwd()
E034 = ROOT / "control/dev_checks/autobuild_build_e034_runner.py"


def load_e034():
    spec = importlib.util.spec_from_file_location("e034", E034)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def guard_git_canary() -> None:
    repo = ROOT / "control/dev_checks/git_guard_e037_repo"
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, text=True)
    subprocess.run(["git", "config", "--local", "user.name", "Prediction Test"], cwd=repo, check=True, text=True)
    subprocess.run(["git", "config", "--local", "user.email", "prediction-test@example.invalid"], cwd=repo, check=True, text=True)
    try:
        subprocess.run(["git", "config", "--local", "remote.origin.url", "https://example.invalid/x"], cwd=repo, check=True, text=True)
    except PermissionError:
        pass
    else:
        raise AssertionError("GUARD_ALLOWED_REMOTE_CONFIG")
    print("GIT_GUARD_CANARY_PASS")


def main() -> None:
    guard_git_canary()
    load_e034().main()


if __name__ == "__main__":
    main()
