from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
PROD = Path.home() / "prediction_research_prod"
PY = str(PROD / ".venv/bin/python")
DEMO = "control/dev_checks/project_executor_demo_e001.py"
INTENDED = [
    "control/codex_supervisor/build_planner.py",
    "tests/control/test_build_planner_nonbuildable_components.py",
    "tests/control/test_build_planner_retry.py",
    "knowledge/codex_runtime/CONFIG.json",
]


def fail(prefix: str, exc: BaseException) -> None:
    msg = " ".join(str(exc).split())[:2400]
    raise SystemExit(f"{prefix}={exc.__class__.__name__}:{msg}")


def git_prod(*args: str) -> list[str]:
    cp = subprocess.run(
        ["git", *args], cwd=PROD, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    if cp.returncode != 0:
        raise RuntimeError("PROD_GIT:" + (cp.stdout or "")[-1200:])
    return [line.strip() for line in cp.stdout.splitlines() if line.strip()]


def allowed(rel: str) -> bool:
    if rel == DEMO:
        return False
    if rel.startswith("control/project_tasks/") or rel.startswith("control/bridge_commands/inbox/"):
        return False
    return rel.startswith("control/") or rel.startswith("tests/") or rel == "knowledge/codex_runtime/CONFIG.json"


def prepare() -> None:
    changed = set(git_prod("diff", "--name-only", "HEAD"))
    changed |= set(git_prod("ls-files", "--others", "--exclude-standard"))
    for rel in sorted(changed):
        if not allowed(rel):
            continue
        src, dst = PROD / rel, ROOT / rel
        if src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    for rel in INTENDED:
        src, dst = PROD / rel, ROOT / rel
        if not src.is_file():
            raise AssertionError("REQUIRED_LOCAL_FILE_MISSING:" + rel)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    planner = ROOT / INTENDED[0]
    text = planner.read_text(encoding="utf-8")
    markers = [
        "For REQUIRES_SHARED_INFRA or INSUFFICIENT_SPEC, components MUST be an empty list []",
        "NONBUILDABLE_COMPONENTS_MUST_BE_EMPTY",
        "BUILD_PLANNER_RETRY_LIMIT_REACHED",
        "BUILD_PLANNER_COMPLETE_WITHOUT_STATE_ADVANCE",
    ]
    for marker in markers:
        if marker not in text:
            raise AssertionError("PLANNER_MARKER_MISSING:" + marker)

    new_sha = hashlib.sha256(planner.read_bytes()).hexdigest()
    cfg = ROOT / INTENDED[3]
    raw = cfg.read_text(encoding="utf-8")
    obj = json.loads(raw)
    hits: list[tuple[tuple[str, ...], str]] = []

    def walk(value, path: tuple[str, ...] = ()) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                ks = str(key)
                if isinstance(child, str) and re.fullmatch(r"[0-9a-fA-F]{64}", child) and "build_planner" in ks.lower():
                    hits.append((path + (ks,), child))
                if isinstance(child, (dict, list)):
                    walk(child, path + (ks,))
        elif isinstance(value, list):
            for i, child in enumerate(value):
                walk(child, path + (str(i),))

    walk(obj)
    if len(hits) != 1:
        raise AssertionError("BUILD_PLANNER_KEY_COUNT:" + str(len(hits)) + ":" + repr(hits)[:700])
    path, old = hits[0]
    if old != new_sha:
        if raw.count(old) != 1:
            raise AssertionError("BUILD_PLANNER_OLD_PIN_NOT_UNIQUE")
        cfg.write_text(raw.replace(old, new_sha, 1), encoding="utf-8")
    if new_sha not in cfg.read_text(encoding="utf-8"):
        raise AssertionError("BUILD_PLANNER_PIN_NOT_UPDATED")
    print("AUTOBUILD_PREPARED key=" + "/".join(path) + " sha=" + new_sha)


def run_tests() -> None:
    env = os.environ.copy()
    env.pop("PYTEST_ADDOPTS", None)
    log_path = ROOT / "control/dev_checks/pytest_e022.log"
    base = ["-m", "pytest", "-q", f"--log-file={log_path}"]
    stages = [
        ("TARGETED", base + [
            "tests/control/test_build_planner_nonbuildable_components.py",
            "tests/control/test_build_planner_retry.py",
        ]),
        ("WIRING", base + ["tests/codex_supervisor/test_autobuild_runtime_wiring_e004i.py"]),
        ("FULL", base + ["tests"]),
    ]
    for label, args in stages:
        cp = subprocess.run(
            [PY, *args], cwd=ROOT, env=env, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        out = cp.stdout or ""
        if cp.returncode != 0:
            compact = " | ".join(line.strip() for line in out.splitlines()[-24:] if line.strip())[:3000]
            raise SystemExit("TEST_FAIL_" + label + "=" + compact)
        compact = " | ".join(line.strip() for line in out.splitlines()[-5:] if line.strip())[:900]
        print(label + "_PASS " + compact)


def verify_staged() -> None:
    wanted = set(INTENDED)
    cp = subprocess.run(
        ["git", "diff", "--cached", "--name-only"], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    if cp.returncode != 0:
        raise SystemExit("VERIFY_FAIL=CACHED_DIFF:" + (cp.stdout or "")[-800:])
    got = {line.strip() for line in cp.stdout.splitlines() if line.strip()}
    if got != wanted:
        raise SystemExit("VERIFY_FAIL=STAGED_SET_MISMATCH:" + repr(sorted(got)))
    print("STAGED_SET_EXACT")


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "build"
    if mode == "verify":
        verify_staged()
        return
    try:
        prepare()
    except BaseException as exc:
        fail("PREPARE_FAIL", exc)
    run_tests()


if __name__ == "__main__":
    main()
