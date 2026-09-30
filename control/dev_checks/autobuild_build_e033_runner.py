from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
import importlib.util

ROOT = Path.cwd()
E031 = ROOT / "control/dev_checks/autobuild_build_e031_runner.py"
PROD = Path.home() / "prediction_research_prod"
PY = str(PROD / ".venv/bin/python")
CORE_TESTS = {
    "tests/control/test_build_planner_nonbuildable_components.py",
    "tests/control/test_build_planner_retry.py",
}


def load_e031():
    spec = importlib.util.spec_from_file_location("e031", E031)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_pytest(label: str, paths: list[str]) -> str:
    env = os.environ.copy()
    env.pop("PYTEST_ADDOPTS", None)
    log_path = ROOT / "control/dev_checks/pytest_e033.log"
    cp = subprocess.run(
        [PY, "-m", "pytest", "-q", "--tb=line", f"--log-file={log_path}", *paths],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    out = cp.stdout or ""
    lines = [line.strip() for line in out.splitlines() if line.strip()]
    if cp.returncode != 0:
        interesting = [
            line for line in lines
            if line.startswith("E ")
            or "AssertionError" in line
            or "Blocked:" in line
            or "SOURCE_CHANGED" in line
            or "FAILED " in line
            or "ERROR " in line
        ]
        payload = interesting[-14:] if interesting else lines[-24:]
        raise SystemExit("TEST_FAIL_" + label + "=" + " | ".join(payload)[:3800])
    return " | ".join(lines[-5:])[:900]


def main() -> None:
    m = load_e031()
    base = m.load_base()
    base.prepare()
    pinned = m.sync_pins(base)

    summaries = []
    summaries.append("TARGETED " + run_pytest("TARGETED", sorted(CORE_TESTS)))
    summaries.append("WIRING " + run_pytest(
        "WIRING", ["tests/codex_supervisor/test_autobuild_runtime_wiring_e004i.py"]
    ))
    summaries.append("FULL " + run_pytest("FULL", ["tests"]))

    allowed = pinned | CORE_TESTS | {"knowledge/codex_runtime/CONFIG.json"}
    stage = m.changed(allowed)
    required = CORE_TESTS | {
        "control/codex_supervisor/build_planner.py",
        "control/codex_supervisor/candidate_dispatch.py",
        "knowledge/codex_runtime/CONFIG.json",
    }
    if not required <= stage:
        raise SystemExit("STAGE_REQUIRED_MISSING=" + repr(sorted(required - stage)))

    m.git("diff", "--check", "--", *sorted(stage))
    m.git("add", "--", *sorted(stage))
    got = {line.strip() for line in m.git("diff", "--cached", "--name-only").splitlines() if line.strip()}
    if got != stage:
        raise SystemExit("STAGED_SET_MISMATCH=" + repr(sorted(got)) + " expected=" + repr(sorted(stage)))

    final_obj = json.loads(m.CONFIG.read_text(encoding="utf-8"))
    mismatches = []

    def verify(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if isinstance(child, str) and re.fullmatch(r"[0-9a-fA-F]{64}", child) and str(key).endswith("_sha256"):
                    rel = m.resolve_pin(str(key))
                    if rel and child != m.sha(ROOT / rel):
                        mismatches.append((str(key), rel, child, m.sha(ROOT / rel)))
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
