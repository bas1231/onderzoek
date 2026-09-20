from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from validator import Task
from policy_check import check_action
from jobs.lifecycle_ledger import (
    load_record as lifecycle_load,
    update as lifecycle_update,
)


ROOT = Path(__file__).resolve().parents[1]

PENDING = ROOT / "control/tasks/pending"
RUNNING = ROOT / "control/tasks/running"
COMPLETED = ROOT / "control/tasks/completed"
FAILED = ROOT / "control/tasks/failed"
RESULTS = ROOT / "control/results"
TASK_QUEUE = ROOT / "control/TASK_QUEUE.yaml"

def load_work_cadence():
    path = ROOT / 'control/hourly/work_cadence.py'
    spec = importlib.util.spec_from_file_location(
        'prediction_research_executor_work_cadence',
        path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f'cannot load work cadence from {path}')
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.modules.pop(spec.name, None)
        raise
    return mod

WORK_CADENCE = load_work_cadence()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def git(*args: str, check: bool = True):
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=check,
    )


def current_commit() -> str:
    return git("rev-parse", "HEAD").stdout.strip()


def push_head_best_effort() -> bool:
    """
    Push completed local research history to the private Git remote.

    A remote failure never erases local evidence.
    """
    result = git(
        "push",
        "origin",
        "HEAD:main",
        check=False,
    )

    if result.returncode == 0:
        print("Git push: PASS")
        return True

    print("Git push: FAILED")
    if result.stderr:
        print(result.stderr.strip())

    return False


def research_queue_paused() -> bool:
    if not TASK_QUEUE.exists():
        return True

    for line in TASK_QUEUE.read_text().splitlines():
        stripped = line.strip()

        if stripped.startswith("queue_status:"):
            status = stripped.split(":", 1)[1].strip()
            return status != "ACTIVE"

    return True


def task_is_committed(task_file: Path) -> bool:
    """
    Process a task only after the task file exists in Git HEAD.

    This prevents the executor from racing with a human or director
    that is still creating/staging/committing the task.
    """
    try:
        relative = task_file.relative_to(ROOT).as_posix()
    except ValueError:
        return False

    probe = git(
        "cat-file",
        "-e",
        f"HEAD:{relative}",
        check=False,
    )

    return probe.returncode == 0


def process_task(task_file: Path) -> str:
    raw = json.loads(task_file.read_text())
    task = Task.model_validate(raw)

    if task.task_class == "research" and research_queue_paused():
        print(
            f"{task.task_id}: research queue paused; "
            "task left pending"
        )
        return "paused"

    lifecycle = lifecycle_load(task.task_id)

    cadence_result = WORK_CADENCE.check(
        reason=f'executor_task:{task.task_id}',
    )
    if not cadence_result.get('allowed'):
        reason = str(cadence_result.get('reason', 'CADENCE_BLOCKED'))
        print(
            f'{task.task_id}: executor blocked by work cadence: {reason}'
        )
        return 'cadence_blocked'

    if lifecycle.get("state") != "ACCEPTED":
        print(
            f"{task.task_id}: waiting for durable "
            "bridge ACCEPTED state"
        )
        return "awaiting_accept"

    running_file = RUNNING / task_file.name
    shutil.move(task_file, running_file)

    lifecycle_update(
        task.task_id,
        "RUNNING",
        "executor claimed pending task",
    )

    started_at = now_iso()
    source_commit = current_commit()

    workdir = (ROOT / task.working_directory).resolve()

    if ROOT not in workdir.parents and workdir != ROOT:
        raise RuntimeError(
            "working directory escaped repository"
        )

    stdout = ""
    stderr = ""
    exit_code = None
    status = "failed"

    command_text = " ".join(task.command)

    policy_result = check_action(command_text)

    execution_provenance = {
        "executor_commit": current_commit(),
        "policy_status": policy_result["status"],
        "policy_reason": policy_result["reason"],
        "command_text": command_text,
    }

    if policy_result["status"] == "BLOCKED_BY_POLICY":
        result_dir = RESULTS / task.task_id
        result_dir.mkdir(parents=True, exist_ok=True)

        blocked_result = {
            "task_id": task.task_id,
            "status": "BLOCKED_BY_POLICY",
            "reason": policy_result["reason"],
            "command": task.command,
            "execution_provenance": execution_provenance,
            "timestamp": now_iso()
        }

        (result_dir / "RESULT.json").write_text(
            json.dumps(
                blocked_result,
                indent=2,
                sort_keys=True
            ) + "\n"
        )

        lifecycle_update(
            task.task_id,
            "BLOCKED_BY_POLICY",
            policy_result["reason"],
        )

        return "blocked"

    try:
        proc = subprocess.run(
            task.command,
            cwd=workdir,
            text=True,
            capture_output=True,
            timeout=task.timeout_seconds,
        )

        stdout = proc.stdout
        stderr = proc.stderr
        exit_code = proc.returncode
        status = (
            "completed"
            if exit_code == 0
            else "failed"
        )

    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = (exc.stderr or "") + "\nTASK TIMEOUT"
        exit_code = 124
        status = "failed"

    finished_at = now_iso()

    result_dir = RESULTS / task.task_id
    result_dir.mkdir(parents=True, exist_ok=True)

    stdout_file = result_dir / "stdout.log"
    stderr_file = result_dir / "stderr.log"

    stdout_file.write_text(stdout)
    stderr_file.write_text(stderr)

    result = {
        "task_id": task.task_id,
        "hypothesis_id": task.hypothesis_id,
        "task_class": task.task_class,
        "status": status,
        "source_commit": source_commit,
        "started_at": started_at,
        "finished_at": finished_at,
        "exit_code": exit_code,
        "command": task.command,
        "stdout_sha256": sha256_file(stdout_file),
        "stderr_sha256": sha256_file(stderr_file),
    }

    result_file = result_dir / "RESULT.json"

    result_file.write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        ) + "\n"
    )

    destination = (
        COMPLETED if status == "completed" else FAILED
    ) / running_file.name

    shutil.move(running_file, destination)

    lifecycle_update(
        task.task_id,
        "COMPLETED"
        if status == "completed"
        else "FAILED",
        "executor finished task",
    )

    git(
        "add",
        "control/tasks",
        "control/results",
        "evidence",
    )

    staged = git(
        "diff",
        "--cached",
        "--quiet",
        check=False,
    )

    if staged.returncode != 0:
        git(
            "commit",
            "-m",
            f"result({task.task_id}): {status}",
        )
        push_head_best_effort()

    print(
        f"{task.task_id}: {status} "
        f"(exit={exit_code})"
    )

    return status


def record_infrastructure_failure(
    task_file: Path,
    exc: Exception,
) -> None:
    try:
        running_file = RUNNING / task_file.name

        source = (
            running_file
            if running_file.exists()
            else task_file
        )

        destination = FAILED / task_file.name

        if source.exists():
            shutil.move(source, destination)

        error_dir = RESULTS / task_file.stem
        error_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        (error_dir / "INFRA_ERROR.txt").write_text(
            f"{type(exc).__name__}: {exc}\n"
        )

        git(
            "add",
            "control/tasks",
            "control/results",
        )

        staged = git(
            "diff",
            "--cached",
            "--quiet",
            check=False,
        )

        if staged.returncode != 0:
            git(
                "commit",
                "-m",
                (
                    f"result({task_file.stem}): "
                    "infrastructure failure"
                ),
            )
            push_head_best_effort()

    except Exception as handling_exc:
        print(
            "ERROR recording infrastructure failure:",
            handling_exc,
        )


def main() -> None:
    for directory in (
        PENDING,
        RUNNING,
        COMPLETED,
        FAILED,
        RESULTS,
    ):
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    print("Prediction Research executor started")

    while True:
        tasks = sorted(PENDING.glob("*.json"))

        if not tasks:
            time.sleep(5)
            continue

        paused_seen = False
        awaiting_accept_seen = False

        for task_file in tasks:
            if not task_is_committed(task_file):
                continue

            try:
                outcome = process_task(task_file)

                if outcome == "paused":
                    paused_seen = True
                elif outcome == "awaiting_accept":
                    awaiting_accept_seen = True

            except Exception as exc:
                print(
                    f"ERROR processing "
                    f"{task_file.name}: {exc}"
                )

                record_infrastructure_failure(
                    task_file,
                    exc,
                )

        if paused_seen:
            time.sleep(30)
        elif awaiting_accept_seen:
            time.sleep(5)


if __name__ == "__main__":
    main()
