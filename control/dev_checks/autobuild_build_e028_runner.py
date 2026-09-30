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
INTENDED = [
    "control/codex_supervisor/build_planner.py",
    "control/codex_supervisor/candidate_dispatch.py",
    "tests/control/test_build_planner_nonbuildable_components.py",
    "tests/control/test_build_planner_retry.py",
    "knowledge/codex_runtime/CONFIG.json",
]


def git_prod(*args: str) -> list[str]:
    cp = subprocess.run(["git", *args], cwd=PROD, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if cp.returncode != 0:
        raise RuntimeError("PROD_GIT:" + (cp.stdout or "")[-1200:])
    return [line.strip() for line in cp.stdout.splitlines() if line.strip()]


def copy_rel(rel: str) -> None:
    src, dst = PROD / rel, ROOT / rel
    if src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def pin_sha(raw: str, obj: object, key_fragment: str, new_sha: str) -> str:
    hits: list[tuple[tuple[str, ...], str]] = []

    def walk(value: object, path: tuple[str, ...] = ()) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                ks = str(key)
                if isinstance(child, str) and re.fullmatch(r"[0-9a-fA-F]{64}", child) and key_fragment in ks.lower():
                    hits.append((path + (ks,), child))
                if isinstance(child, (dict, list)):
                    walk(child, path + (ks,))
        elif isinstance(value, list):
            for i, child in enumerate(value):
                walk(child, path + (str(i),))

    walk(obj)
    if len(hits) != 1:
        raise AssertionError(f"PIN_KEY_COUNT:{key_fragment}:{len(hits)}:{hits!r}")
    _path, old = hits[0]
    if old == new_sha:
        return raw
    if raw.count(old) != 1:
        raise AssertionError(f"PIN_OLD_NOT_UNIQUE:{key_fragment}")
    return raw.replace(old, new_sha, 1)


def prepare() -> None:
    # Reproduce the current local test/control context inside the isolated worktree.
    context = set(git_prod("ls-files", "tests", "control/codex_supervisor"))
    context |= set(git_prod("ls-files", "--others", "--exclude-standard", "tests", "control/codex_supervisor"))
    for rel in sorted(context):
        copy_rel(rel)
    for rel in INTENDED:
        if not (PROD / rel).is_file():
            raise AssertionError("REQUIRED_LOCAL_FILE_MISSING:" + rel)
        copy_rel(rel)

    planner = ROOT / "control/codex_supervisor/build_planner.py"
    ptext = planner.read_text(encoding="utf-8")
    for marker in [
        "For REQUIRES_SHARED_INFRA or INSUFFICIENT_SPEC, components MUST be an empty list []",
        "NONBUILDABLE_COMPONENTS_MUST_BE_EMPTY",
        "BUILD_PLANNER_RETRY_LIMIT_REACHED",
        "BUILD_PLANNER_COMPLETE_WITHOUT_STATE_ADVANCE",
    ]:
        if marker not in ptext:
            raise AssertionError("PLANNER_MARKER_MISSING:" + marker)

    dispatch = ROOT / "control/codex_supervisor/candidate_dispatch.py"
    dtext = dispatch.read_text(encoding="utf-8")
    old = "    if state=='NEEDS_BUILD':\n        repo=P(task['candidate_source_root'])"
    new = "    if state=='NEEDS_BUILD' and protocols:\n        repo=P(task['candidate_source_root'])"
    if old in dtext:
        if dtext.count(old) != 1:
            raise AssertionError("NEEDS_BUILD_PROTOCOL_BRANCH_NOT_UNIQUE")
        dispatch.write_text(dtext.replace(old, new, 1), encoding="utf-8")
    elif new not in dtext:
        raise AssertionError("NEEDS_BUILD_PROTOCOL_BRANCH_NOT_FOUND")

    cfg = ROOT / "knowledge/codex_runtime/CONFIG.json"
    raw = cfg.read_text(encoding="utf-8")
    obj = json.loads(raw)
    raw = pin_sha(raw, obj, "build_planner", hashlib.sha256(planner.read_bytes()).hexdigest())
    obj = json.loads(raw)
    raw = pin_sha(raw, obj, "candidate_dispatch", hashlib.sha256(dispatch.read_bytes()).hexdigest())
    cfg.write_text(raw, encoding="utf-8")


def run_pytest(label: str, paths: list[str]) -> str:
    env = os.environ.copy()
    env.pop("PYTEST_ADDOPTS", None)
    log_path = ROOT / "control/dev_checks/pytest_e028.log"
    args = [PY, "-m", "pytest", "-q", f"--log-file={log_path}", *paths]
    cp = subprocess.run(args, cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = cp.stdout or ""
    if cp.returncode != 0:
        compact = " | ".join(line.strip() for line in out.splitlines()[-36:] if line.strip())[:3800]
        raise SystemExit("TEST_FAIL_" + label + "=" + compact)
    return " | ".join(line.strip() for line in out.splitlines()[-5:] if line.strip())[:900]


def verify_staged() -> None:
    wanted = set(INTENDED)
    cp = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
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
        raise SystemExit("PREPARE_FAIL=" + exc.__class__.__name__ + ":" + " ".join(str(exc).split())[:2400])

    summaries = []
    summaries.append("TARGETED " + run_pytest("TARGETED", [
        "tests/control/test_build_planner_nonbuildable_components.py",
        "tests/control/test_build_planner_retry.py",
    ]))
    summaries.append("WIRING " + run_pytest("WIRING", [
        "tests/codex_supervisor/test_autobuild_runtime_wiring_e004i.py",
    ]))
    summaries.append("FULL " + run_pytest("FULL", ["tests"]))
    print("AUTOBUILD_TESTS_PASS " + " || ".join(summaries))


if __name__ == "__main__":
    main()
