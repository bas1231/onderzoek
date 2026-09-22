#!/usr/bin/env python3
from __future__ import annotations

import json
import py_compile
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control"))

from executor_preflight import sync_main_fail_closed, support_script_in_head  # noqa: E402


def run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)


def must(cp: subprocess.CompletedProcess[str], label: str) -> None:
    if cp.returncode != 0:
        raise AssertionError(f"{label}: rc={cp.returncode} stdout={cp.stdout} stderr={cp.stderr}")


def config_repo(repo: Path) -> None:
    must(run(repo, "git", "config", "user.email", "transport-test@example.invalid"), "git email")
    must(run(repo, "git", "config", "user.name", "Transport Test"), "git name")


def commit_file(repo: Path, rel: str, content: str, message: str) -> str:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    must(run(repo, "git", "add", "--", rel), f"add {rel}")
    must(run(repo, "git", "commit", "-m", message), f"commit {rel}")
    return run(repo, "git", "rev-parse", "HEAD").stdout.strip()


def make_origin(tmp: Path) -> tuple[Path, Path]:
    origin = tmp / "origin.git"
    seed = tmp / "seed"
    must(run(tmp, "git", "init", "--bare", str(origin)), "init bare")
    must(run(tmp, "git", "init", "-b", "main", str(seed)), "init seed")
    config_repo(seed)
    commit_file(seed, "README.md", "base\n", "base")
    must(run(seed, "git", "remote", "add", "origin", str(origin)), "add origin")
    must(run(seed, "git", "push", "-u", "origin", "main"), "push base")
    must(run(origin, "git", "symbolic-ref", "HEAD", "refs/heads/main"), "origin head")
    return origin, seed


def clone(origin: Path, target: Path) -> Path:
    must(run(target.parent, "git", "clone", str(origin), str(target)), "clone")
    config_repo(target)
    return target


def check_1_technical() -> dict:
    py_compile.compile(str(ROOT / "control/executor_preflight.py"), doraise=True)
    py_compile.compile(str(ROOT / "control/executor.py"), doraise=True)

    with tempfile.TemporaryDirectory(prefix="executor-030-tech-") as td:
        tmp = Path(td)
        origin, _ = make_origin(tmp)
        repo = clone(origin, tmp / "executor")
        out = sync_main_fail_closed(repo)
        assert out["ok"] is True
        assert out["status"] == "ALREADY_CURRENT"

        commit_file(repo, "control/jobs/tracked.py", "print('ok')\n", "tracked script")
        must(run(repo, "git", "push", "origin", "main"), "push tracked")
        task = SimpleNamespace(operation="python", command=["python3", "control/jobs/tracked.py"])
        support = support_script_in_head(repo, task)
        assert support["ok"] is True

    return {"pass": True, "compile": True, "basic_sync": "PASS", "tracked_support": "PASS"}


def check_2_adversarial() -> dict:
    cases: dict[str, str] = {}

    # Dirty tracked worktree must block without altering the file.
    with tempfile.TemporaryDirectory(prefix="executor-030-dirty-") as td:
        tmp = Path(td)
        origin, _ = make_origin(tmp)
        repo = clone(origin, tmp / "executor")
        readme = repo / "README.md"
        readme.write_text("local dirty\n", encoding="utf-8")
        out = sync_main_fail_closed(repo)
        assert out["ok"] is False and out["reason"] == "TRACKED_WORKTREE_DIRTY"
        assert readme.read_text(encoding="utf-8") == "local dirty\n"
        cases["dirty_tracked"] = "PASS"

    # Missing and untracked support scripts must never execute.
    with tempfile.TemporaryDirectory(prefix="executor-030-support-") as td:
        tmp = Path(td)
        origin, _ = make_origin(tmp)
        repo = clone(origin, tmp / "executor")
        missing = SimpleNamespace(operation="python", command=["python3", "control/jobs/missing.py"])
        out = support_script_in_head(repo, missing)
        assert out["ok"] is False and out["reason"] == "SUPPORT_SCRIPT_MISSING_ON_DISK"
        p = repo / "control/jobs/untracked.py"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("print('no')\n", encoding="utf-8")
        untracked = SimpleNamespace(operation="python", command=["python3", "control/jobs/untracked.py"])
        out = support_script_in_head(repo, untracked)
        assert out["ok"] is False and out["reason"] == "SUPPORT_SCRIPT_NOT_TRACKED_IN_HEAD"
        cases["missing_support"] = "PASS"
        cases["untracked_support"] = "PASS"

    # Fetch failure must block.
    with tempfile.TemporaryDirectory(prefix="executor-030-fetch-") as td:
        tmp = Path(td)
        origin, _ = make_origin(tmp)
        repo = clone(origin, tmp / "executor")
        must(run(repo, "git", "remote", "set-url", "origin", str(tmp / "does-not-exist.git")), "bad remote")
        out = sync_main_fail_closed(repo)
        assert out["ok"] is False and out["reason"] == "FETCH_ORIGIN_MAIN_FAILED"
        cases["fetch_failure"] = "PASS"

    # True divergence must block and preserve local commit.
    with tempfile.TemporaryDirectory(prefix="executor-030-diverge-") as td:
        tmp = Path(td)
        origin, seed = make_origin(tmp)
        repo = clone(origin, tmp / "executor")
        local_sha = commit_file(repo, "local.txt", "local\n", "local only")
        commit_file(seed, "remote.txt", "remote\n", "remote only")
        must(run(seed, "git", "push", "origin", "main"), "push remote divergence")
        out = sync_main_fail_closed(repo)
        assert out["ok"] is False and out["reason"] == "DIVERGED_HISTORY"
        assert run(repo, "git", "rev-parse", "HEAD").stdout.strip() == local_sha
        cases["diverged_history"] = "PASS"

    return {"pass": True, "cases": cases}


def check_3_realistic_replay() -> dict:
    # Reproduce incident 029: executor clone is old; origin receives support script
    # and pending task atomically in a later commit. Preflight must fast-forward,
    # after which the support script is both present and tracked.
    with tempfile.TemporaryDirectory(prefix="executor-030-replay-") as td:
        tmp = Path(td)
        origin, seed = make_origin(tmp)
        executor = clone(origin, tmp / "executor")
        before = run(executor, "git", "rev-parse", "HEAD").stdout.strip()

        script_rel = "control/jobs/weather_a19c2_transport_recover.py"
        task_rel = "control/tasks/pending/WEATHER-A19C2-RECOVER-TEST.json"
        script = seed / script_rel
        task = seed / task_rel
        script.parent.mkdir(parents=True, exist_ok=True)
        task.parent.mkdir(parents=True, exist_ok=True)
        script.write_text("print('transport-recovered')\n", encoding="utf-8")
        task.write_text('{"task_id":"WEATHER-A19C2-RECOVER-TEST"}\n', encoding="utf-8")
        must(run(seed, "git", "add", "--", script_rel, task_rel), "stage atomic support+task")
        must(run(seed, "git", "commit", "-m", "atomic transport payload"), "commit atomic support+task")
        remote_commit = run(seed, "git", "rev-parse", "HEAD").stdout.strip()
        must(run(seed, "git", "push", "origin", "main"), "push atomic support+task")

        assert not (executor / script_rel).exists()
        sync = sync_main_fail_closed(executor)
        assert sync["ok"] is True and sync["status"] == "FAST_FORWARDED"
        assert run(executor, "git", "rev-parse", "HEAD").stdout.strip() == remote_commit

        support_task = SimpleNamespace(operation="python", command=["python3", script_rel])
        support = support_script_in_head(executor, support_task)
        assert support["ok"] is True
        cp = run(executor, "python3", script_rel)
        assert cp.returncode == 0 and cp.stdout.strip() == "transport-recovered"

        return {
            "pass": True,
            "old_head": before,
            "new_head": remote_commit,
            "sync_status": sync["status"],
            "support_provenance": support["status"],
            "execution": "PASS",
        }


def main() -> int:
    result = {
        "task_id": "CONTROL-TRANSPORT-STALE-CHECKOUT-030",
        "economic_conclusion": "NO_PROVEN_EDGE",
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
        "checks": {},
    }
    try:
        result["checks"]["check_1_technical"] = check_1_technical()
        result["checks"]["check_2_adversarial_fail_closed"] = check_2_adversarial()
        result["checks"]["check_3_realistic_stale_checkout_replay"] = check_3_realistic_replay()
        result["status"] = "PASS"
        result["next_gate"] = "BOOTSTRAP_RUNNING_EXECUTOR_THEN_RETRY_A19C2_WITH_NEW_TASK_ID"
        code = 0
    except Exception as exc:
        result["status"] = "FAILED"
        result["failure"] = f"{type(exc).__name__}: {exc}"
        result["next_gate"] = "FIX_CONTROL_TRANSPORT_VALIDATION"
        code = 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
