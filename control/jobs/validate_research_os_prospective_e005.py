from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET_BRANCH = "ai/research-os-v1-prospective-validation"
REMOTE_REF = f"origin/{TARGET_BRANCH}"
WORKTREE = ROOT / "experiments/bridge/worktrees/research_os_v1_prospective_e005"
PYTHON = ROOT / ".venv/bin/python"
if not PYTHON.exists():
    PYTHON = Path(sys.executable)

EXPECTED_TREES = {
    "control/research_os_v1": "50f26c84d58d30714d53439d2e55699b18936091",
    "tests/research_os_v1": "a2e390e64c9df7a5c0bfcccbf92abf5937e178dc",
    "benchmarks/research_os_v1": "370584867096e736c9ea9680133eca82febe0952",
}
EXPECTED_DOCS = {
    "docs/PLUS_NATIVE_RESEARCH_OS_CANARY.md": "8594f048f95cb5b7177e17279c934de8eb49861e",
    "docs/RESEARCH_OS_V1_DECISION_LOG.md": "e9710bd29647cc67c6ecfd8146d5e3bcafe4a7fd",
    "docs/RESEARCH_OS_V1_INDEX.md": "a071938a8ea3fd0da7684a5a30ed3d65df669636",
    "docs/RESEARCH_OS_V1_PREBUILD_AUDIT.md": "72f428011f18be55150f99fa1fedbd81d8ace1b8",
    "docs/RESEARCH_OS_V1_PREBUILD_SPEC.md": "c62605bd2a22a2f384cee82ad6810241bd173d92",
    "docs/RESEARCH_OS_V1_ROLLOUT_PLAN.md": "d86356e1f10ad42278065665c45864a13faf05d4",
    "docs/RESEARCH_OS_V1_WORKER_CONTRACTS.md": "af02ebadf893c4f1aec41f67047b568d1443ff78",
}
ALLOWED_PREFIXES = (
    "control/research_os_v1/",
    "tests/research_os_v1/",
    "benchmarks/research_os_v1/",
)
ALLOWED_EXACT = frozenset(EXPECTED_DOCS)

records: list[dict] = []
failed = False


def run(label: str, argv: list[str], *, cwd: Path = ROOT, timeout: int = 600, required: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    global failed
    proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
    records.append({
        "label": label,
        "argv": argv,
        "cwd": str(cwd),
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-20000:],
        "stderr_tail": proc.stderr[-20000:],
        "required": required,
    })
    print(f"=== {label} rc={proc.returncode} ===")
    if proc.stdout:
        print(proc.stdout[-20000:])
    if proc.stderr:
        print(proc.stderr[-20000:], file=sys.stderr)
    if required and proc.returncode != 0:
        failed = True
    return proc


def git_text(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def tree_sha(ref: str, path: str) -> str:
    return git_text("rev-parse", f"{ref}:{path}")


def allowed_path(path: str) -> bool:
    return path in ALLOWED_EXACT or any(path.startswith(prefix) for prefix in ALLOWED_PREFIXES)


def find_packet_dir(root: Path) -> Path | None:
    counts: dict[Path, int] = {}
    excluded = {".git", ".venv", "node_modules", "__pycache__"}
    for path in root.rglob("*.json"):
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        if any(part in excluded for part in rel.parts):
            continue
        try:
            if path.stat().st_size > 2_000_000:
                continue
            obj = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("agent_id"), str):
            counts[path.parent] = counts.get(path.parent, 0) + 1
    if not counts:
        return None
    return sorted(counts, key=lambda p: (counts[p], p.as_posix()), reverse=True)[0]


def clean_env() -> dict[str, str]:
    env = dict(os.environ)
    secret_fragments = (
        "TOKEN", "SECRET", "PASSWORD", "PASSWD", "API_KEY", "APIKEY",
        "PRIVATE_KEY", "ACCESS_KEY", "KALSHI", "POLYMARKET", "OPENAI_API",
    )
    for key in list(env):
        upper = key.upper()
        if any(fragment in upper for fragment in secret_fragments):
            env.pop(key, None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env

try:
    run("fetch_validation_branch", ["git", "fetch", "origin", TARGET_BRANCH, "main"], timeout=180)

    target_head = git_text("rev-parse", REMOTE_REF)
    main_head = git_text("rev-parse", "origin/main")
    records.append({"label": "heads", "required": True, "returncode": 0, "target_head": target_head, "main_head": main_head})

    ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", "origin/main", REMOTE_REF], cwd=ROOT)
    records.append({"label": "current_main_is_ancestor", "required": True, "returncode": ancestor.returncode})
    if ancestor.returncode != 0:
        failed = True

    for path, expected in EXPECTED_TREES.items():
        actual = tree_sha(REMOTE_REF, path)
        ok = actual == expected
        records.append({"label": "prospective_tree_hash", "path": path, "expected": expected, "actual": actual, "required": True, "returncode": 0 if ok else 1})
        if not ok:
            failed = True

    for path, expected in EXPECTED_DOCS.items():
        actual = tree_sha(REMOTE_REF, path)
        ok = actual == expected
        records.append({"label": "frozen_doc_hash", "path": path, "expected": expected, "actual": actual, "required": True, "returncode": 0 if ok else 1})
        if not ok:
            failed = True

    diff = run("allowed_diff_scope", ["git", "diff", "--name-only", "origin/main..." + REMOTE_REF], timeout=180)
    diff_paths = [line.strip() for line in diff.stdout.splitlines() if line.strip()]
    bad_paths = [path for path in diff_paths if not allowed_path(path)]
    records.append({"label": "diff_scope_check", "required": True, "returncode": 0 if not bad_paths else 1, "bad_paths": bad_paths, "diff_paths": diff_paths})
    if bad_paths:
        failed = True

    if WORKTREE.exists():
        run("remove_stale_worktree", ["git", "worktree", "remove", "--force", str(WORKTREE)], required=False, timeout=180)
        if WORKTREE.exists():
            shutil.rmtree(WORKTREE)
    WORKTREE.parent.mkdir(parents=True, exist_ok=True)
    run("worktree_prune", ["git", "worktree", "prune"])
    run("worktree_add", ["git", "worktree", "add", "--detach", str(WORKTREE), REMOTE_REF], timeout=180)

    env = clean_env()
    pytest_base = [str(PYTHON), "-m", "pytest", "-q", "-p", "no:cacheprovider"]
    run("compile_research_os", [str(PYTHON), "-m", "compileall", "-q", "control/research_os_v1"], cwd=WORKTREE, timeout=300, env=env)
    run("research_os_tests", pytest_base + ["tests/research_os_v1"], cwd=WORKTREE, timeout=900, env=env)
    run("prebuild_validator", [str(PYTHON), "-m", "control.research_os_v1.validate_prebuild_spec"], cwd=WORKTREE, timeout=300, env=env)
    run("runtime_validator", [str(PYTHON), "-m", "control.research_os_v1.validate_runtime"], cwd=WORKTREE, timeout=300, env=env)
    run("schema_alignment_validator", [str(PYTHON), "-m", "control.research_os_v1.validate_schema_alignment"], cwd=WORKTREE, timeout=300, env=env)
    run("prospective_ready_validator", [str(PYTHON), "-m", "control.research_os_v1.validate_prospective_ready"], cwd=WORKTREE, timeout=300, env=env)
    run("full_regression_tests", pytest_base + ["tests"], cwd=WORKTREE, timeout=1500, env=env)

    packet_dir = find_packet_dir(WORKTREE)
    if packet_dir is None:
        failed = True
        records.append({"label": "real_shadow_packet_discovery", "required": True, "returncode": 1, "detail": "no committed directory containing agent_id JSON packets found"})
    else:
        packet_rel = packet_dir.relative_to(WORKTREE)
        records.append({"label": "real_shadow_packet_discovery", "required": True, "returncode": 0, "packet_dir": packet_rel.as_posix()})
        shadow = run(
            "real_shadow_cli",
            [str(PYTHON), "-m", "control.research_os_v1.shadow_cli", "--candidates", "knowledge/candidates", "--packets", packet_rel.as_posix(), "--source-commit", target_head],
            cwd=WORKTREE,
            timeout=300,
            env=env,
        )
        if shadow.returncode == 0:
            try:
                obj = json.loads(shadow.stdout)
                invariants = {
                    "mode_shadow_read_only": obj.get("mode") == "SHADOW_READ_ONLY",
                    "runtime_mutation_false": obj.get("runtime_mutation") is False,
                    "main_mutation_false": obj.get("main_mutation") is False,
                    "live_trading_false": obj.get("live_trading") is False,
                    "paid_actions_false": obj.get("paid_actions") is False,
                    "wallet_actions_false": obj.get("wallet_actions") is False,
                    "economic_default": obj.get("economic_conclusion") == "NO_PROVEN_EDGE",
                }
                ok = all(invariants.values())
                records.append({"label": "shadow_invariants", "required": True, "returncode": 0 if ok else 1, "invariants": invariants, "input_summary": obj.get("input_summary"), "selected": obj.get("scheduled", {}).get("selected", [])})
                if not ok:
                    failed = True
            except Exception as exc:
                failed = True
                records.append({"label": "shadow_invariants", "required": True, "returncode": 1, "error": f"{type(exc).__name__}: {exc}"})

    tracked = run("tracked_mutation_check", ["git", "status", "--porcelain", "--untracked-files=no"], cwd=WORKTREE)
    if tracked.stdout.strip():
        failed = True
        records.append({"label": "unexpected_tracked_mutation", "required": True, "returncode": 1, "status": tracked.stdout})

finally:
    if WORKTREE.exists():
        run("worktree_cleanup", ["git", "worktree", "remove", "--force", str(WORKTREE)], required=False, timeout=180)
        if WORKTREE.exists():
            shutil.rmtree(WORKTREE)
    run("worktree_prune_final", ["git", "worktree", "prune"], required=False)

summary = {
    "validator": "RESEARCH_OS_V1_PROSPECTIVE_LOCAL_E005",
    "target_branch": TARGET_BRANCH,
    "status": "PASS" if not failed else "FAIL_CLOSED",
    "first_prospective_datapoint_authorized": not failed,
    "automatic_runtime_replacement_authorized": False,
    "live_trading": False,
    "paid_actions": False,
    "wallet_actions": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
    "records": records,
}
print("=== RESEARCH_OS_V1_PROSPECTIVE_VALIDATION_SUMMARY ===")
print(json.dumps(summary, indent=2, sort_keys=True))
raise SystemExit(0 if not failed else 1)
