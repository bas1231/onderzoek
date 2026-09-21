from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BRANCH = "ai/research-os-v1-integration-shadow"
WORKTREE_ROOT = ROOT / "experiments" / "bridge" / "worktrees"
EVIDENCE_DIR = ROOT / "evidence" / "research_os_v1"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: list[str], *, cwd: Path, timeout: int = 1200) -> dict:
    started = now_iso()
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    return {
        "command": cmd,
        "cwd": str(cwd.relative_to(ROOT)) if cwd.is_relative_to(ROOT) else str(cwd),
        "started_at": started,
        "finished_at": now_iso(),
        "exit_code": proc.returncode,
        "stdout_tail": proc.stdout[-12000:],
        "stderr_tail": proc.stderr[-12000:],
    }


def git(*args: str, cwd: Path = ROOT, timeout: int = 300) -> dict:
    return run(["git", *args], cwd=cwd, timeout=timeout)


def main() -> int:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    WORKTREE_ROOT.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    worktree = WORKTREE_ROOT / f"research-os-v1-{stamp}-{os.getpid()}"
    report_path = EVIDENCE_DIR / f"integration_validation_{stamp}.json"

    report: dict = {
        "schema_version": 1,
        "validator": "RESEARCH_OS_V1_LOCAL_INTEGRATION",
        "started_at": now_iso(),
        "branch": BRANCH,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "venue_network_calls": False,
        "steps": [],
        "status": "FAIL_CLOSED",
        "economic_conclusion": "NO_PROVEN_EDGE",
    }

    main_head = git("rev-parse", "HEAD")
    report["steps"].append(main_head)
    report["main_source_commit"] = main_head["stdout_tail"].strip() if main_head["exit_code"] == 0 else None

    cleanup_result = None
    try:
        fetch = git("fetch", "--quiet", "origin", BRANCH)
        report["steps"].append(fetch)
        if fetch["exit_code"] != 0:
            report["failure_reason"] = "git_fetch_failed"
            return_code = 2
            return return_code

        resolve = git("rev-parse", "FETCH_HEAD")
        report["steps"].append(resolve)
        if resolve["exit_code"] != 0:
            report["failure_reason"] = "integration_ref_resolution_failed"
            return 3

        integration_sha = resolve["stdout_tail"].strip()
        report["integration_source_commit"] = integration_sha

        add = git("worktree", "add", "--detach", str(worktree), integration_sha, timeout=600)
        report["steps"].append(add)
        if add["exit_code"] != 0:
            report["failure_reason"] = "worktree_add_failed"
            return 4

        python = ROOT / ".venv" / "bin" / "python"
        python_cmd = str(python) if python.exists() else sys.executable
        report["python"] = python_cmd

        checks = [
            [python_cmd, "-m", "pytest", "-q", "tests/research_os_v1"],
            [python_cmd, "-m", "control.research_os_v1.validate_prebuild_spec"],
            [python_cmd, "-m", "control.research_os_v1.validate_runtime"],
            [python_cmd, "-m", "pytest", "-q", "tests"],
        ]

        all_pass = True
        for command in checks:
            result = run(command, cwd=worktree, timeout=1800)
            report["steps"].append(result)
            if result["exit_code"] != 0:
                all_pass = False
                break

        report["status"] = "PASS" if all_pass else "FAIL_CLOSED"
        report["finished_at"] = now_iso()
        return 0 if all_pass else 10

    except subprocess.TimeoutExpired as exc:
        report["failure_reason"] = "subprocess_timeout"
        report["timeout_command"] = list(exc.cmd) if isinstance(exc.cmd, (list, tuple)) else str(exc.cmd)
        report["finished_at"] = now_iso()
        return 124
    except Exception as exc:
        report["failure_reason"] = f"unexpected:{type(exc).__name__}:{exc}"
        report["finished_at"] = now_iso()
        return 99
    finally:
        if worktree.exists():
            try:
                cleanup_result = git("worktree", "remove", "--force", str(worktree), timeout=600)
                report["cleanup"] = cleanup_result
            except Exception as exc:
                report["cleanup"] = {
                    "exit_code": 99,
                    "error": f"{type(exc).__name__}:{exc}",
                }

        report.setdefault("finished_at", now_iso())
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({
            "status": report.get("status"),
            "report": str(report_path.relative_to(ROOT)),
            "main_source_commit": report.get("main_source_commit"),
            "integration_source_commit": report.get("integration_source_commit"),
            "economic_conclusion": "NO_PROVEN_EDGE",
        }, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
