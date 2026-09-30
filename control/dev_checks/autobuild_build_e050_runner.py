from __future__ import annotations

import importlib.util
import os
import subprocess
import traceback
from pathlib import Path

ROOT = Path.cwd()
PROD = Path.home() / "prediction_research_prod"
PY = str(PROD / ".venv/bin/python")
E031 = ROOT / "control/dev_checks/autobuild_build_e031_runner.py"
E034 = ROOT / "control/dev_checks/autobuild_build_e034_runner.py"
E048 = ROOT / "control/dev_checks/autobuild_build_e048_runner.py"
DISPATCH = ROOT / "control/codex_supervisor/candidate_dispatch.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def patch_candidate_replay() -> None:
    text = DISPATCH.read_text(encoding="utf-8")
    old = "changed=any(old.get('source_hashes')!=hashes for old in prior)"
    new = "changed=bool(prior) and all(old.get('source_hashes')!=hashes for old in prior)"
    if new not in text:
        if text.count(old) != 1:
            raise SystemExit("E050_REPLAY_PATCH_ANCHOR_COUNT=" + str(text.count(old)))
        text = text.replace(old, new, 1)
    protocol_old = "    if state=='NEEDS_BUILD':\n        repo=P(task['candidate_source_root'])"
    protocol_new = "    if state=='NEEDS_BUILD' and protocols:\n        repo=P(task['candidate_source_root'])"
    if protocol_new not in text:
        if text.count(protocol_old) != 1:
            raise SystemExit("E050_PROTOCOL_PATCH_ANCHOR_COUNT=" + str(text.count(protocol_old)))
        text = text.replace(protocol_old, protocol_new, 1)
    DISPATCH.write_text(text, encoding="utf-8")


def exact_lifecycle() -> str:
    runtime = ROOT / "control/dev_checks/pytest_e050"
    tmp_root = runtime / "tmp"
    base_temp = runtime / "basetemp"
    runtime.mkdir(parents=True, exist_ok=True)
    tmp_root.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.pop("PYTEST_ADDOPTS", None)
    for key in ("TMPDIR", "TMP", "TEMP"):
        env[key] = str(tmp_root)
    paths = ["tests/codex_supervisor/test_candidate_dispatch.py"]
    sol = ROOT / "tests/codex_supervisor/test_sol_builder_route.py"
    if sol.is_file():
        paths.append("tests/codex_supervisor/test_sol_builder_route.py")
    cp = subprocess.run(
        [PY, "-m", "pytest", "-vv", "--tb=short", f"--basetemp={base_temp}", *paths],
        cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    out = cp.stdout or ""
    if cp.returncode:
        lines = [line.rstrip() for line in out.splitlines() if line.strip()]
        failed = [line for line in lines if line.startswith("FAILED ") or "AssertionError" in line or line.lstrip().startswith("E ")]
        tail = failed[-24:] if failed else lines[-70:]
        raise SystemExit("E050_LIFECYCLE_FAIL=" + " | ".join(tail)[:7000])
    return " | ".join([line.strip() for line in out.splitlines()[-8:] if line.strip()])[:1200]


def git(*args: str) -> str:
    cp = subprocess.run(["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if cp.returncode:
        raise SystemExit("E050_GIT_FAIL=" + " ".join(args) + ":" + (cp.stdout or "")[-1800:])
    return cp.stdout or ""


def main() -> None:
    e048 = load(E048, "e048_for_e050")
    copied = e048.sync_python_sources()
    e048.patch_bridge_import_fail_closed()

    e031 = load(E031, "e031_for_e050")
    e034 = load(E034, "e034_for_e050")
    base = e031.load_base()
    original_prepare = base.prepare

    def prepared() -> None:
        original_prepare()
        patch_candidate_replay()

    original_run = e034.guarded_pytest
    lifecycle_done = {"value": False, "summary": ""}

    def run_pytest(label: str, paths: list[str]) -> str:
        if label == "FULL" and not lifecycle_done["value"]:
            lifecycle_done["summary"] = exact_lifecycle()
            lifecycle_done["value"] = True
        return original_run(label, paths)

    base.prepare = prepared
    base.run_pytest = run_pytest
    e031.load_base = lambda: base
    e031.main()

    safety_family = {
        "control/browser_bridge.py",
        "control/browser_bridge_core.py",
        "control/executor.py",
        "control/executor_preflight.py",
        "control/git_local_only.py",
    }
    safety_stage = e048.changed({p for p in safety_family if (ROOT / p).is_file()})
    if "control/browser_bridge.py" in safety_stage:
        git("diff", "--check", "--", *sorted(safety_stage))
        git("add", "--", *sorted(safety_stage))

    staged = {line.strip() for line in git("diff", "--cached", "--name-only").splitlines() if line.strip()}
    required = {
        "control/codex_supervisor/build_planner.py",
        "control/codex_supervisor/candidate_dispatch.py",
        "knowledge/codex_runtime/CONFIG.json",
        "tests/control/test_build_planner_nonbuildable_components.py",
        "tests/control/test_build_planner_retry.py",
    }
    if not required <= staged:
        raise SystemExit("E050_REQUIRED_STAGE_MISSING=" + repr(sorted(required - staged)))

    print(
        "E050_ALL_TESTS_PASS lifecycle=" + lifecycle_done["summary"]
        + " | staged=" + repr(sorted(staged))
        + " | source_snapshot_count=" + str(len(copied))
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException as exc:
        tb = traceback.format_exc().splitlines()
        tail = " | ".join(line.strip() for line in tb[-10:] if line.strip())
        raise SystemExit("E050_BUILD_FAIL=" + exc.__class__.__name__ + ":" + " ".join(str(exc).split())[:1800] + " | " + tail[:2600])
