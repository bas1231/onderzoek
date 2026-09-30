from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path

ROOT = Path.cwd()
BASE = ROOT / "control/dev_checks/autobuild_build_e028_runner.py"
CONFIG = ROOT / "knowledge/codex_runtime/CONFIG.json"
PROD = Path.home() / "prediction_research_prod"
CORE_TESTS = {
    "tests/control/test_build_planner_nonbuildable_components.py",
    "tests/control/test_build_planner_retry.py",
}
EXPLICIT_PIN_PATHS = {
    "supervisor_sha256": "control/codex_supervisor/supervisor.py",
    "candidate_policy_sha256": "control/hourly/candidate_queue.py",
}


def load_base():
    spec = importlib.util.spec_from_file_location("e028", BASE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    cp = subprocess.run(
        ["git", *args], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    if cp.returncode:
        raise SystemExit("GIT_FAIL=" + " ".join(args) + ":" + (cp.stdout or "")[-1200:])
    return cp.stdout or ""


def resolve_pin(key: str) -> str | None:
    if key in EXPLICIT_PIN_PATHS:
        return EXPLICIT_PIN_PATHS[key]
    if key.endswith(".py_sha256"):
        filename = key[:-7]
        candidates = [
            f"control/codex_supervisor/{filename}",
            f"control/hourly/{filename}",
        ]
        existing = [rel for rel in candidates if (ROOT / rel).is_file()]
        if len(existing) > 1:
            raise AssertionError("AMBIGUOUS_PIN_SOURCE:" + key + ":" + repr(existing))
        return existing[0] if existing else None
    return None


def sync_pins(base) -> set[str]:
    # candidate_policy is outside the E028 context; copy it explicitly so its
    # pinned source and CONFIG are tested from the same local snapshot.
    candidate_policy = "control/hourly/candidate_queue.py"
    if (PROD / candidate_policy).is_file():
        base.copy_rel(candidate_policy)

    obj = json.loads(CONFIG.read_text(encoding="utf-8"))
    pinned: set[str] = set()

    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                ks = str(key)
                if isinstance(child, str) and re.fullmatch(r"[0-9a-fA-F]{64}", child) and ks.endswith("_sha256"):
                    rel = resolve_pin(ks)
                    if rel:
                        src = ROOT / rel
                        if not src.is_file():
                            raise AssertionError("PIN_SOURCE_MISSING:" + ks + ":" + rel)
                        value[key] = sha(src)
                        pinned.add(rel)
                elif isinstance(child, (dict, list)):
                    walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(obj)
    required_keys = {"supervisor_sha256", "candidate_policy_sha256"}
    top_keys = set(obj) if isinstance(obj, dict) else set()
    if not required_keys <= top_keys:
        raise AssertionError("REQUIRED_PIN_KEYS_MISSING:" + repr(sorted(required_keys - top_keys)))
    if "control/codex_supervisor/supervisor.py" not in pinned:
        raise AssertionError("SUPERVISOR_PIN_NOT_RESOLVED")
    CONFIG.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return pinned


def changed(paths: set[str]) -> set[str]:
    if not paths:
        return set()
    ordered = sorted(paths)
    out = git("diff", "--name-only", "--", *ordered)
    out += git("ls-files", "--others", "--exclude-standard", "--", *ordered)
    return {line.strip() for line in out.splitlines() if line.strip()}


def main() -> None:
    base = load_base()
    base.prepare()
    pinned = sync_pins(base)

    summaries = []
    summaries.append("TARGETED " + base.run_pytest("TARGETED", sorted(CORE_TESTS)))
    summaries.append("WIRING " + base.run_pytest(
        "WIRING", ["tests/codex_supervisor/test_autobuild_runtime_wiring_e004i.py"]
    ))
    summaries.append("FULL " + base.run_pytest("FULL", ["tests"]))

    allowed = pinned | CORE_TESTS | {"knowledge/codex_runtime/CONFIG.json"}
    stage = changed(allowed)
    required = CORE_TESTS | {
        "control/codex_supervisor/build_planner.py",
        "control/codex_supervisor/candidate_dispatch.py",
        "knowledge/codex_runtime/CONFIG.json",
    }
    if not required <= stage:
        raise SystemExit("STAGE_REQUIRED_MISSING=" + repr(sorted(required - stage)))

    git("diff", "--check", "--", *sorted(stage))
    git("add", "--", *sorted(stage))
    got = {line.strip() for line in git("diff", "--cached", "--name-only").splitlines() if line.strip()}
    if got != stage:
        raise SystemExit("STAGED_SET_MISMATCH=" + repr(sorted(got)) + " expected=" + repr(sorted(stage)))

    # Final provenance assertion: every resolvable CONFIG pin equals the source
    # bytes that are about to be committed/tested in this worktree.
    final_obj = json.loads(CONFIG.read_text(encoding="utf-8"))
    mismatches = []
    def verify(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if isinstance(child, str) and re.fullmatch(r"[0-9a-fA-F]{64}", child) and str(key).endswith("_sha256"):
                    rel = resolve_pin(str(key))
                    if rel and child != sha(ROOT / rel):
                        mismatches.append((str(key), rel, child, sha(ROOT / rel)))
                elif isinstance(child, (dict, list)):
                    verify(child)
        elif isinstance(value, list):
            for child in value:
                verify(child)
    verify(final_obj)
    if mismatches:
        raise SystemExit("PIN_MISMATCH=" + repr(mismatches)[:2500])

    print("AUTOBUILD_TESTS_PASS staged=" + str(len(stage)) + " " + " || ".join(summaries))


if __name__ == "__main__":
    main()
