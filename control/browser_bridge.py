from __future__ import annotations

import json
import secrets
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

from validator import Task
from jobs.lifecycle_ledger import update as lifecycle_update


ROOT = Path(__file__).resolve().parents[1]

CONFIG_DIR = Path.home() / ".config/prediction-research"
TOKEN_FILE = CONFIG_DIR / "bridge_token"
STATE_FILE = CONFIG_DIR / "bridge_state.json"

PENDING = ROOT / "control/tasks/pending"
RESULTS = ROOT / "control/results"

HOST = "127.0.0.1"
PORT = 8765

LOCK = threading.RLock()


class FileWrite(BaseModel):
    path: str
    content: str

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        path = Path(value)

        if path.is_absolute():
            raise ValueError("absolute paths forbidden")

        if ".." in path.parts:
            raise ValueError("parent traversal forbidden")

        allowed = (
            "experiments/bridge/",
            "control/jobs/",
            "tests/bridge/",
        )

        text = path.as_posix()

        if not text.startswith(allowed):
            raise ValueError(
                "bridge file writes restricted to "
                "experiments/bridge/, control/jobs/, tests/bridge/"
            )

        return value


class BridgeEnvelope(BaseModel):
    bridge_version: int = 1
    commit_message: str = Field(min_length=3, max_length=160)
    files: list[FileWrite] = []
    task: Task

    @field_validator("commit_message")
    @classmethod
    def safe_commit_message(cls, value: str) -> str:
        if "\n" in value or "\r" in value:
            raise ValueError("multiline commit message forbidden")
        return value


def git(*args: str, check: bool = True):
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=check,
    )


def queue_status() -> str:
    queue = ROOT / "control/TASK_QUEUE.yaml"

    if not queue.exists():
        return "MISSING"

    for line in queue.read_text(errors="replace").splitlines():
        stripped = line.strip()

        if stripped.startswith("queue_status:"):
            return stripped.split(":", 1)[1].strip()

    return "UNKNOWN"


def ensure_token() -> str:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if not TOKEN_FILE.exists():
        TOKEN_FILE.write_text(secrets.token_urlsafe(48) + "\n")
        TOKEN_FILE.chmod(0o600)

    return TOKEN_FILE.read_text().strip()


TOKEN = ensure_token()


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {
            "bridge_tasks": [],
            "acked": [],
        }

    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {
            "bridge_tasks": [],
            "acked": [],
        }


def save_state(state: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    STATE_FILE.write_text(
        json.dumps(
            state,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    STATE_FILE.chmod(0o600)


def task_exists(task_id: str) -> bool:
    locations = [
        ROOT / "control/tasks/pending",
        ROOT / "control/tasks/running",
        ROOT / "control/tasks/completed",
        ROOT / "control/tasks/failed",
        ROOT / "control/results",
    ]

    for location in locations:
        if (location / f"{task_id}.json").exists():
            return True

        if (location / task_id).exists():
            return True

    return False


def commit_and_push(
    message: str,
    stage_paths: list[str] | None = None,
) -> tuple[bool, str]:
    if stage_paths is None:
        stage_paths = [
            "control/tasks",
            "experiments/bridge",
            "control/jobs",
            "tests/bridge",
        ]

    existing_paths = [
        path
        for path in stage_paths
        if (ROOT / path).exists()
    ]

    if not existing_paths:
        return False, "nothing to stage"

    added = git(
        "add",
        "--",
        *existing_paths,
        check=False,
    )

    if added.returncode != 0:
        return False, (
            "git add failed: "
            + added.stderr.strip()
        )

    staged = git(
        "diff",
        "--cached",
        "--quiet",
        check=False,
    )

    if staged.returncode == 0:
        return False, "nothing to commit"

    commit = git(
        "commit",
        "-m",
        message,
        check=False,
    )

    if commit.returncode != 0:
        return False, (
            "git commit failed: "
            + commit.stderr.strip()
        )

    pushed = git(
        "push",
        "origin",
        "HEAD:main",
        check=False,
    )

    if pushed.returncode != 0:
        return True, (
            "committed locally; remote push failed: "
            + pushed.stderr.strip()
        )

    return True, "committed and pushed"


def enqueue(envelope: BridgeEnvelope) -> dict:
    task = envelope.task

    with LOCK:
        if (
            task.task_class == "research"
            and queue_status() != "ACTIVE"
        ):
            return {
                "ok": False,
                "error": "research queue is paused",
                "queue_status": queue_status(),
            }

        task_rel = (
            "control/tasks/pending/"
            + task.task_id
            + ".json"
        )

        task_path = ROOT / task_rel

        stage_paths = [
            file_write.path
            for file_write in envelope.files
        ] + [task_rel]

        if task_exists(task.task_id):
            recovered = False
            detail = "existing task"

            if task_path.exists():
                committed_check = git(
                    "cat-file",
                    "-e",
                    "HEAD:" + task_rel,
                    check=False,
                )

                if committed_check.returncode != 0:
                    committed, detail = commit_and_push(
                        envelope.commit_message,
                        stage_paths,
                    )

                    if not committed:
                        print(
                            "[bridge] recovery failed "
                            f"task_id={task.task_id} "
                            f"detail={detail}"
                        )

                        return {
                            "ok": False,
                            "error": detail,
                            "recoverable": True,
                        }

                    recovered = True
                else:
                    detail = (
                        "existing committed task"
                    )

            state = load_state()

            if (
                task.task_id
                not in state["bridge_tasks"]
            ):
                state["bridge_tasks"].append(
                    task.task_id
                )

            save_state(state)

            print(
                "[bridge] idempotent enqueue "
                f"task_id={task.task_id} "
                f"recovered={recovered}"
            )

            return {
                "ok": True,
                "task_id": task.task_id,
                "duplicate": True,
                "recovered": recovered,
                "git": detail,
                "queue_status": queue_status(),
            }

        for file_write in envelope.files:
            target = ROOT / file_write.path

            target.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            target.write_text(
                file_write.content,
                encoding="utf-8",
            )

        PENDING.mkdir(
            parents=True,
            exist_ok=True,
        )

        tmp_path = (
            PENDING /
            f".{task.task_id}.tmp"
        )

        tmp_path.write_text(
            json.dumps(
                task.model_dump(),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        tmp_path.replace(task_path)

        committed, detail = commit_and_push(
            envelope.commit_message,
            stage_paths,
        )

        if not committed:
            print(
                "[bridge] enqueue commit failed "
                f"task_id={task.task_id} "
                f"detail={detail}"
            )

            return {
                "ok": False,
                "error": detail,
                "recoverable": True,
            }

        state = load_state()

        if (
            task.task_id
            not in state["bridge_tasks"]
        ):
            state["bridge_tasks"].append(
                task.task_id
            )

        save_state(state)

        lifecycle_update(
            task.task_id,
            "ACCEPTED",
            "bridge enqueue accepted",
        )

        print(
            "[bridge] enqueue accepted "
            f"task_id={task.task_id}"
        )

        return {
            "ok": True,
            "task_id": task.task_id,
            "git": detail,
            "queue_status": queue_status(),
        }


def next_outbox_item() -> dict | None:
    state = load_state()

    bridge_tasks = state.get("bridge_tasks", [])
    acked = set(state.get("acked", []))

    for task_id in bridge_tasks:
        if task_id in acked:
            continue

        result_dir = RESULTS / task_id
        result_file = result_dir / "RESULT.json"

        if not result_file.exists():
            continue

        result = json.loads(result_file.read_text())

        stdout_file = result_dir / "stdout.log"
        stderr_file = result_dir / "stderr.log"

        stdout = (
            stdout_file.read_text(errors="replace")[:20000]
            if stdout_file.exists()
            else ""
        )

        stderr = (
            stderr_file.read_text(errors="replace")[:20000]
            if stderr_file.exists()
            else ""
        )

        lifecycle_update(
            task_id,
            "DELIVERED",
            "bridge outbox exposed result",
        )

        return {
            "task_id": task_id,
            "result": result,
            "stdout": stdout,
            "stderr": stderr,
            "git_head": git(
                "rev-parse",
                "--short",
                "HEAD",
            ).stdout.strip(),
        }

    return None


def acknowledge(task_id: str) -> dict:
    state = load_state()

    if task_id not in state.get("bridge_tasks", []):
        return {
            "ok": False,
            "error": "unknown bridge task",
        }

    acked = state.setdefault("acked", [])

    if task_id not in acked:
        acked.append(task_id)

    save_state(state)

    lifecycle_update(
        task_id,
        "ACKED",
        "browser acknowledged result",
    )

    return {
        "ok": True,
        "task_id": task_id,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "PredictionResearchBridge/0.1"

    def log_message(self, fmt, *args):
        print(
            "%s - %s"
            % (
                self.address_string(),
                fmt % args,
            )
        )

    def send_json(self, status: int, payload: dict):
        body = json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ).encode()

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def authorized(self) -> bool:
        expected = f"Bearer {TOKEN}"
        return self.headers.get("Authorization", "") == expected

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))

        if length <= 0 or length > 2_000_000:
            raise ValueError("invalid request size")

        body = self.rfile.read(length)
        return json.loads(body)

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/health":
            self.send_json(
                200,
                {
                    "status": "ok",
                    "queue_status": queue_status(),
                    "git_head": git(
                        "rev-parse",
                        "--short",
                        "HEAD",
                    ).stdout.strip(),
                },
            )
            return

        if not self.authorized():
            self.send_json(401, {"error": "unauthorized"})
            return

        if path == "/outbox":
            self.send_json(
                200,
                {
                    "item": next_outbox_item()
                },
            )
            return

        if path.startswith("/result/"):
            task_id = path[len("/result/"):]

            allowed = set(
                "abcdefghijklmnopqrstuvwxyz"
                "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                "0123456789-_."
            )

            if (
                not task_id
                or len(task_id) > 160
                or any(ch not in allowed for ch in task_id)
            ):
                self.send_json(
                    400,
                    {"error": "invalid task_id"},
                )
                return

            result_dir = RESULTS / task_id
            result_file = result_dir / "RESULT.json"

            if not result_file.exists():
                self.send_json(
                    404,
                    {
                        "task_id": task_id,
                        "status": "pending"
                    },
                )
                return

            result = json.loads(
                result_file.read_text()
            )

            stdout_file = result_dir / "stdout.log"
            stderr_file = result_dir / "stderr.log"

            self.send_json(
                200,
                {
                    "task_id": task_id,
                    "result": result,
                    "stdout": (
                        stdout_file.read_text(
                            errors="replace"
                        )[:12000]
                        if stdout_file.exists()
                        else ""
                    ),
                    "stderr": (
                        stderr_file.read_text(
                            errors="replace"
                        )[:12000]
                        if stderr_file.exists()
                        else ""
                    ),
                    "git_head": git(
                        "rev-parse",
                        "--short",
                        "HEAD",
                    ).stdout.strip(),
                },
            )
            return

        self.send_json(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path

        if not self.authorized():
            self.send_json(401, {"error": "unauthorized"})
            return

        try:
            payload = self.read_json()

            with LOCK:
                if path == "/enqueue":
                    envelope = BridgeEnvelope.model_validate(payload)
                    result = enqueue(envelope)

                    self.send_json(
                        200 if result.get("ok") else 409,
                        result,
                    )
                    return

                if path == "/ack":
                    task_id = str(payload.get("task_id", ""))
                    result = acknowledge(task_id)

                    self.send_json(
                        200 if result.get("ok") else 404,
                        result,
                    )
                    return

            self.send_json(404, {"error": "not found"})

        except Exception as exc:
            self.send_json(
                400,
                {
                    "error": type(exc).__name__,
                    "detail": str(exc),
                },
            )


def main():
    print(
        f"Prediction Research Browser Bridge listening "
        f"on http://{HOST}:{PORT}"
    )

    server = ThreadingHTTPServer(
        (HOST, PORT),
        Handler,
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Bridge stopping.")


if __name__ == "__main__":
    main()
