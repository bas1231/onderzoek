from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET_BRANCH = "ai/research-os-v1-frozen-validation"
REMOTE_REF = f"origin/{TARGET_BRANCH}"
MAIN_REF = "origin/main"
WORKTREE = ROOT / "experiments/bridge/worktrees/research_os_v1_frozen_e003"
PYTHON = ROOT / ".venv/bin/python"
if not PYTHON.is_file():
    PYTHON = Path(sys.executable)

EXPECTED_TREES = {
    "control/research_os_v1": "22bf1f4cb530dc15b4dd09e3b8944bc7675ce5c8",
    "tests/research_os_v1": "7bd82afa2a128ef75a6bc799eafbce95989dff6d",
    "benchmarks/research_os_v1": "844910dddef2e078324a155f4d61f8b4c2b0bfe3",
}
EXPECTED_DOC_BLOBS = {
    "docs/PLUS_NATIVE_RESEARCH_OS_CANARY.md": "8594f048f95cb5b7177e17279c934de8eb49861e",
    "docs/RESEARCH_OS_V1_DECISION_LOG.md": "e9710bd29647cc67c6ecfd8146d5e3bcafe4a7fd",
    "docs/RESEARCH_OS_V1_INDEX.md": "a071938a8ea3fd0da7684a5a30ed3d65df669636",
    "docs/RESEARCH_OS_V1_PREBUILD_AUDIT.md": "72f428011f18be55150f99fa1fedbd81d8ace1b8",
    "docs/RESEARCH_OS_V1_PREBUILD_SPEC.md": "c62605bd2a22a2f384cee82ad6810241bd173d92",
    "docs/RESEARCH_OS_V1_ROLLOUT_PLAN.md": "d86356e1f10ad42278065665c45864a13faf05d4",
    "docs/RESEARCH_OS_V1_WORKER_CONTRACTS.md": "af02ebadf893c4f1aec41f67047b568d1443ff78",
}
ALLOWED_DIFF_PREFIXES = (
    "control/research_os_v1/",
    "tests/research_os_v1/",
    "benchmarks/research_os_v1/",
)
ALLOWED_DIFF_EXACT = set(EXPECTED_DOC_BLOBS)

records: list[dict] = []
failed = False


def safe_env() -> dict[str, str]:
    env = dict(os.environ)
    sensitive = (
        "TOKEN", "SECRET", "PASSWORD", "PASSWD", "CREDENTIAL",
        "PRIVATE_KEY", "API_KEY", "KALSHI", "POLYMARKET", "WALLET",
        "MNEMONIC", "SEED_PHRASE",
    )
    for key in list(env):
        upper = key.upper()
        if any(fragment in upper for fragment in sensitive):
            env.pop(key, None)
    home = WORKTREE / ".validation_home"
    home.mkdir(parents=True, exist_ok=True)
    env["HOME"] = str(home)
    env["XDG_CONFIG_HOME"] = str(home / ".config")
    env["XDG_CACHE_HOME"] = str(home / ".cache")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(WORKTREE)
    env["RESEARCH_OS_VALIDATION"] = "1"
    return env


def run(label: str, argv: list[str], *, cwd: Path = ROOT, timeout: int = 900,
        required: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    global failed
    try:
        proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                              timeout=timeout, env=env)
    except subprocess.TimeoutExpired as exc:
        proc = subprocess.CompletedProcess(
            argv, 124,
            stdout=(exc.stdout or "") if isinstance(exc.stdout, str) else "",
            stderr=((exc.stderr or "") if isinstance(exc.stderr, str) else "") + "\nTIMEOUT",
        )
    records.append({
        "label": label,
        "argv": argv,
        "cwd": str(cwd),
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-16000:],
        "stderr_tail": proc.stderr[-16000:],
        "required": required,
    })
    print(f"=== {label} rc={proc.returncode} ===")
    if proc.stdout:
        print(proc.stdout[-16000:])
    if proc.stderr:
        print(proc.stderr[-16000:], file=sys.stderr)
    if required and proc.returncode != 0:
        failed = True
    return proc


def rev_parse(spec: str) -> str:
    proc = run(f"rev_parse:{spec}", ["git", "rev-parse", spec], timeout=60)
    return proc.stdout.strip()


def find_packet_dir(root: Path) -> Path | None:
    counts: dict[Path, int] = {}
    excluded = {".git", ".venv", ".validation_home", "__pycache__", "node_modules", "tests", "worktrees"}
    for path in root.rglob("*.json"):
        if any(part in excluded for part in path.parts):
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
    return max(counts, key=lambda p: (counts[p], p.as_posix()))


try:
    run("fetch_main_and_validation", ["git", "fetch", "origin", "main", TARGET_BRANCH], timeout=180)

    if WORKTREE.exists():
        run("remove_stale_worktree", ["git", "worktree", "remove", "--force", str(WORKTREE)], required=False, timeout=180)
        if WORKTREE.exists():
            shutil.rmtree(WORKTREE)
    run("worktree_prune", ["git", "worktree", "prune"], required=False)

    main_head = rev_parse(MAIN_REF)
    target_head = rev_parse(REMOTE_REF)

    ancestry = run(
        "validation_contains_current_main",
        ["git", "merge-base", "--is-ancestor", MAIN_REF, REMOTE_REF],
        timeout=60,
    )
    records.append({
        "label": "snapshot_heads",
        "required": True,
        "returncode": 0 if ancestry.returncode == 0 else 1,
        "main_head": main_head,
        "target_head": target_head,
    })

    for path, expected in {**EXPECTED_TREES, **EXPECTED_DOC_BLOBS}.items():
        actual = rev_parse(f"{REMOTE_REF}:{path}")
        if actual != expected:
            failed = True
            records.append({
                "label": "frozen_object_mismatch",
                "required": True,
                "returncode": 1,
                "path": path,
                "expected": expected,
                "actual": actual,
            })

    diff = run(
        "sidecar_diff_scope",
        ["git", "diff", "--name-only", f"{MAIN_REF}..{REMOTE_REF}"],
        timeout=120,
    )
    diff_paths = [line.strip() for line in diff.stdout.splitlines() if line.strip()]
    unexpected = [
        path for path in diff_paths
        if path not in ALLOWED_DIFF_EXACT
        and not any(path.startswith(prefix) for prefix in ALLOWED_DIFF_PREFIXES)
    ]
    if unexpected:
        failed = True
        records.append({
            "label": "unexpected_diff_paths",
            "required": True,
            "returncode": 1,
            "paths": unexpected,
        })

    if not failed:
        WORKTREE.parent.mkdir(parents=True, exist_ok=True)
        run("worktree_add", ["git", "worktree", "add", "--detach", str(WORKTREE), REMOTE_REF], timeout=180)
        env = safe_env()
        pytest_base = [str(PYTHON), "-m", "pytest", "-q", "-p", "no:cacheprovider"]

        run("research_os_tests", pytest_base + ["tests/research_os_v1"], cwd=WORKTREE, timeout=900, env=env)
        run("prebuild_validator", [str(PYTHON), "-m", "control.research_os_v1.validate_prebuild_spec"], cwd=WORKTREE, timeout=300, env=env)
        run("runtime_validator", [str(PYTHON), "-m", "control.research_os_v1.validate_runtime"], cwd=WORKTREE, timeout=300, env=env)
        run("schema_alignment_validator", [str(PYTHON), "-m", "control.research_os_v1.validate_schema_alignment"], cwd=WORKTREE, timeout=300, env=env)
        run("full_regression_tests", pytest_base + ["tests"], cwd=WORKTREE, timeout=1800, env=env)

        packet_dir = find_packet_dir(WORKTREE)
        if packet_dir is None:
            failed = True
            records.append({
                "label": "real_shadow_packet_discovery",
                "required": True,
                "returncode": 1,
                "detail": "no committed directory containing agent_id JSON packets found",
            })
        else:
            packet_rel = packet_dir.relative_to(WORKTREE).as_posix()
            records.append({
                "label": "real_shadow_packet_discovery",
                "required": True,
                "returncode": 0,
                "packet_dir": packet_rel,
            })
            shadow = run(
                "real_shadow_cli",
                [str(PYTHON), "-m", "control.research_os_v1.shadow_cli",
                 "--candidates", "knowledge/candidates",
                 "--packets", packet_rel,
                 "--source-commit", target_head],
                cwd=WORKTREE,
                timeout=300,
                env=env,
            )
            if shadow.returncode == 0:
                try:
                    obj = json.loads(shadow.stdout)
                except Exception as exc:
                    failed = True
                    records.append({"label": "shadow_json_parse", "required": True, "returncode": 1, "error": f"{type(exc).__name__}: {exc}"})
                else:
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
                    records.append({
                        "label": "shadow_invariants",
                        "required": True,
                        "returncode": 0 if ok else 1,
                        "invariants": invariants,
                        "input_summary": obj.get("input_summary"),
                        "invalid_task_count": len(obj.get("invalid_tasks") or {}),
                    })
                    if not ok:
                        failed = True

        tracked = run("tracked_mutation_check", ["git", "status", "--porcelain", "--untracked-files=no"], cwd=WORKTREE, timeout=60, env=env)
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
    "validator": "RESEARCH_OS_V1_FROZEN_LOCAL_E003",
    "target_branch": TARGET_BRANCH,
    "status": "PASS" if not failed else "FAIL_CLOSED",
    "live_trading": False,
    "paid_actions": False,
    "wallet_actions": False,
    "credentials_available_to_test_subprocesses": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
    "records": records,
}
print("=== RESEARCH_OS_V1_FROZEN_VALIDATION_SUMMARY ===")
print(json.dumps(summary, indent=2, sort_keys=True))
raise SystemExit(0 if not failed else 1)
