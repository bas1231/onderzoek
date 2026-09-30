from __future__ import annotations

import importlib.util
import shutil
import subprocess
import traceback
from pathlib import Path

ROOT = Path.cwd()
PROD = Path.home() / "prediction_research_prod"
E039 = ROOT / "control/dev_checks/autobuild_build_e039_runner.py"
E034 = ROOT / "control/dev_checks/autobuild_build_e034_runner.py"
BRIDGE = ROOT / "control/browser_bridge.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git(*args: str) -> str:
    cp = subprocess.run(["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if cp.returncode:
        raise SystemExit("E048_GIT_FAIL=" + " ".join(args) + ":" + (cp.stdout or "")[-1800:])
    return cp.stdout or ""


def sync_python_sources() -> list[str]:
    copied: list[str] = []
    for path in PROD.rglob("*.py"):
        try:
            rel = path.relative_to(PROD)
        except ValueError:
            continue
        if any(part in {".git", ".venv", "__pycache__", "tests"} for part in rel.parts):
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


def patch_bridge_import_fail_closed() -> None:
    text = BRIDGE.read_text(encoding="utf-8")
    marker = "NO_PUBLISH_HOOK_UNAVAILABLE"
    new_probe = '''try:\n    _loaded_probe = git("rev-parse", "HEAD", check=False)\nexcept RuntimeError as exc:\n    if str(exc) != "NO_PUBLISH_HOOK_UNAVAILABLE":\n        raise\n    # Read-only bridge surfaces may still load. Enqueue remains fail-closed\n    # because an unknown loaded/current HEAD can never pass its attestation.\n    _loaded_probe = None\n_LOADED_BRIDGE_COMMIT = (\n    _loaded_probe.stdout.strip()\n    if _loaded_probe is not None and _loaded_probe.returncode == 0\n    else ""\n)'''
    new_current = '''def _current_head() -> str:\n    try:\n        probe = git("rev-parse", "HEAD", check=False)\n    except RuntimeError as exc:\n        if str(exc) != "NO_PUBLISH_HOOK_UNAVAILABLE":\n            raise\n        return ""\n    return probe.stdout.strip() if probe.returncode == 0 else ""'''
    if new_probe in text and new_current in text:
        return

    old_probe = '''_loaded_probe = git("rev-parse", "HEAD", check=False)\n_LOADED_BRIDGE_COMMIT = (\n    _loaded_probe.stdout.strip()\n    if _loaded_probe.returncode == 0\n    else ""\n)'''
    old_current = '''def _current_head() -> str:\n    probe = git("rev-parse", "HEAD", check=False)\n    return probe.stdout.strip() if probe.returncode == 0 else ""'''
    if old_probe not in text or old_current not in text:
        hits = []
        lines = text.splitlines()
        for idx, line in enumerate(lines):
            if marker in line or "_loaded_probe" in line or "def _current_head" in line:
                lo = max(0, idx - 5)
                hi = min(len(lines), idx + 8)
                hits.append(" | ".join(f"{n+1}:{lines[n].strip()}" for n in range(lo, hi)))
        raise SystemExit("E048_BRIDGE_PATCH_ANCHOR_MISSING=" + " || ".join(hits)[:3800])
    text = text.replace(old_probe, new_probe, 1).replace(old_current, new_current, 1)
    BRIDGE.write_text(text, encoding="utf-8")


def changed(paths: set[str]) -> set[str]:
    ordered = sorted(paths)
    if not ordered:
        return set()
    out = git("diff", "--name-only", "--", *ordered)
    out += git("ls-files", "--others", "--exclude-standard", "--", *ordered)
    return {line.strip() for line in out.splitlines() if line.strip()}


def main() -> None:
    copied = sync_python_sources()
    patch_bridge_import_fail_closed()

    e034 = load(E034, "e034_for_e048")
    outbox = e034.guarded_pytest("OUTBOX", ["tests/hourly/test_ai_bridge_outbox.py"])
    no_autopush_path = ROOT / "tests/executor/test_no_autopush.py"
    no_autopush = "NOT_PRESENT"
    if no_autopush_path.is_file():
        no_autopush = e034.guarded_pytest("NOAUTOPUSH", ["tests/executor/test_no_autopush.py"])

    e039 = load(E039, "e039_for_e048")
    e039.main()

    safety_family = {
        "control/browser_bridge.py",
        "control/browser_bridge_core.py",
        "control/executor.py",
        "control/executor_preflight.py",
        "control/git_local_only.py",
    }
    safety_stage = changed({p for p in safety_family if (ROOT / p).is_file()})
    if "control/browser_bridge.py" not in safety_stage:
        raise SystemExit("E048_BROWSER_BRIDGE_NOT_CHANGED")
    git("diff", "--check", "--", *sorted(safety_stage))
    git("add", "--", *sorted(safety_stage))

    staged = {line.strip() for line in git("diff", "--cached", "--name-only").splitlines() if line.strip()}
    unexpected_safety = {p for p in staged if p.startswith("control/") and p in safety_family and p not in safety_stage}
    if unexpected_safety:
        raise SystemExit("E048_UNEXPECTED_SAFETY_STAGE=" + repr(sorted(unexpected_safety)))

    print(
        "E048_REPAIR_TESTS_PASS "
        + "OUTBOX=" + outbox
        + " | NOAUTOPUSH=" + no_autopush
        + " | safety_stage=" + repr(sorted(safety_stage))
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
        raise SystemExit(
            "E048_BUILD_FAIL=" + exc.__class__.__name__ + ":"
            + " ".join(str(exc).split())[:1800]
            + " | " + tail[:2600]
        )
