from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET_BRANCH = "ai/research-os-v1-frozen-validation"
EXPECTED_HEAD = "a0d9ba659e529c0cfc9e2eb8e2c38342312c0539"
REMOTE_REF = f"origin/{TARGET_BRANCH}"
WORKTREE = ROOT / "experiments/bridge/worktrees/research_os_v1_frozen_e001"
PYTHON = ROOT / ".venv/bin/python"
if not PYTHON.is_file():
    PYTHON = Path(sys.executable)

records: list[dict] = []
failed = False


def safe_env() -> dict[str, str]:
    env = dict(os.environ)
    sensitive_fragments = (
        "TOKEN",
        "SECRET",
        "PASSWORD",
        "PASSWD",
        "CREDENTIAL",
        "PRIVATE_KEY",
        "API_KEY",
        "KALSHI",
        "POLYMARKET",
        "WALLET",
        "MNEMONIC",
        "SEED_PHRASE",
    )
    for key in list(env):
        upper = key.upper()
        if any(fragment in upper for fragment in sensitive_fragments):
            env.pop(key, None)

    validation_home = WORKTREE / ".validation_home"
    validation_home.mkdir(parents=True, exist_ok=True)
    env["HOME"] = str(validation_home)
    env["XDG_CONFIG_HOME"] = str(validation_home / ".config")
    env["XDG_CACHE_HOME"] = str(validation_home / ".cache")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(WORKTREE)
    env["RESEARCH_OS_VALIDATION"] = "1"
    return env


def run(
    label: str,
    argv: list[str],
    *,
    cwd: Path = ROOT,
    timeout: int = 900,
    required: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    global failed
    try:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        proc = subprocess.CompletedProcess(
            argv,
            124,
            stdout=(exc.stdout or "") if isinstance(exc.stdout, str) else "",
            stderr=((exc.stderr or "") if isinstance(exc.stderr, str) else "") + "\nTIMEOUT",
        )

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


def find_packet_dir(root: Path) -> Path | None:
    counts: dict[Path, int] = {}
    excluded = {
        ".git",
        ".venv",
        ".validation_home",
        "__pycache__",
        "node_modules",
        "tests",
        "worktrees",
    }
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
    return max(counts, key=lambda path: (counts[path], path.as_posix()))


try:
    fetch = run(
        "fetch_frozen_branch",
        ["git", "fetch", "origin", TARGET_BRANCH],
        timeout=180,
    )

    if WORKTREE.exists():
        run(
            "remove_stale_worktree",
            ["git", "worktree", "remove", "--force", str(WORKTREE)],
            required=False,
            timeout=180,
        )
        if WORKTREE.exists():
            shutil.rmtree(WORKTREE)

    run("worktree_prune", ["git", "worktree", "prune"], required=False)

    remote = run("remote_head", ["git", "rev-parse", REMOTE_REF], timeout=60)
    remote_head = remote.stdout.strip()
    if remote.returncode != 0 or remote_head != EXPECTED_HEAD:
        failed = True
        records.append({
            "label": "frozen_head_match",
            "required": True,
            "returncode": 1,
            "expected": EXPECTED_HEAD,
            "actual": remote_head,
        })
    else:
        records.append({
            "label": "frozen_head_match",
            "required": True,
            "returncode": 0,
            "head": remote_head,
        })

    if not failed:
        WORKTREE.parent.mkdir(parents=True, exist_ok=True)
        run(
            "worktree_add",
            ["git", "worktree", "add", "--detach", str(WORKTREE), REMOTE_REF],
            timeout=180,
        )

        local = run("worktree_head", ["git", "rev-parse", "HEAD"], cwd=WORKTREE)
        local_head = local.stdout.strip()
        if local.returncode != 0 or local_head != EXPECTED_HEAD:
            failed = True
            records.append({
                "label": "worktree_head_match",
                "required": True,
                "returncode": 1,
                "expected": EXPECTED_HEAD,
                "actual": local_head,
            })

        env = safe_env()
        pytest_base = [str(PYTHON), "-m", "pytest", "-q", "-p", "no:cacheprovider"]

        run(
            "research_os_tests",
            pytest_base + ["tests/research_os_v1"],
            cwd=WORKTREE,
            timeout=900,
            env=env,
        )
        run(
            "prebuild_validator",
            [str(PYTHON), "-m", "control.research_os_v1.validate_prebuild_spec"],
            cwd=WORKTREE,
            timeout=300,
            env=env,
        )
        run(
            "runtime_validator",
            [str(PYTHON), "-m", "control.research_os_v1.validate_runtime"],
            cwd=WORKTREE,
            timeout=300,
            env=env,
        )
        run(
            "schema_alignment_validator",
            [str(PYTHON), "-m", "control.research_os_v1.validate_schema_alignment"],
            cwd=WORKTREE,
            timeout=300,
            env=env,
        )
        run(
            "full_regression_tests",
            pytest_base + ["tests"],
            cwd=WORKTREE,
            timeout=1800,
            env=env,
        )

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
                [
                    str(PYTHON),
                    "-m",
                    "control.research_os_v1.shadow_cli",
                    "--candidates",
                    "knowledge/candidates",
                    "--packets",
                    packet_rel,
                    "--source-commit",
                    EXPECTED_HEAD,
                ],
                cwd=WORKTREE,
                timeout=300,
                env=env,
            )
            if shadow.returncode == 0:
                try:
                    obj = json.loads(shadow.stdout)
                except Exception as exc:
                    failed = True
                    records.append({
                        "label": "shadow_json_parse",
                        "required": True,
                        "returncode": 1,
                        "error": f"{type(exc).__name__}: {exc}",
                    })
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

        tracked = run(
            "tracked_mutation_check",
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=WORKTREE,
            timeout=60,
            env=env,
        )
        if tracked.stdout.strip():
            failed = True
            records.append({
                "label": "unexpected_tracked_mutation",
                "required": True,
                "returncode": 1,
                "status": tracked.stdout,
            })

finally:
    if WORKTREE.exists():
        run(
            "worktree_cleanup",
            ["git", "worktree", "remove", "--force", str(WORKTREE)],
            required=False,
            timeout=180,
        )
        if WORKTREE.exists():
            shutil.rmtree(WORKTREE)
    run("worktree_prune_final", ["git", "worktree", "prune"], required=False)

summary = {
    "validator": "RESEARCH_OS_V1_FROZEN_LOCAL_E001",
    "target_branch": TARGET_BRANCH,
    "expected_head": EXPECTED_HEAD,
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
