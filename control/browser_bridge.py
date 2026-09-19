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


ROOT = Path(__file__).resolve().parents[1]

CONFIG_DIR = Path.home() / ".config/prediction-research"
TOKEN_FILE = CONFIG_DIR / "bridge_token"
STATE_FILE = CONFIG_DIR / "bridge_state.json"

PENDING = ROOT / "control/tasks/pending"
RESULTS = ROOT / "control/results"

HOST = "127.0.0.1"
PORT = 8765

LOCK = threading.Lock()


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


def commit_and_push(message: str) -> tuple[bool, str]:
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

    if existing_paths:
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
        return False, commit.stderr.strip()

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

    if task.task_class == "research" and queue_status() != "ACTIVE":
        return {
            "ok": False,
            "error": "research queue is paused",
            "queue_status": queue_status(),
        }

    if task_exists(task.task_id):
        return {
            "ok": False,
            "error": "task_id already exists",
        }

    for file_write in envelope.files:
        target = ROOT / file_write.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(file_write.content)

    PENDING.mkdir(parents=True, exist_ok=True)

    task_path = PENDING / f"{task.task_id}.json"
    tmp_path = PENDING / f".{task.task_id}.tmp"

    tmp_path.write_text(
        json.dumps(
            task.model_dump(),
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    tmp_path.replace(task_path)

    committed, detail = commit_and_push(
        envelope.commit_message
    )

    if not committed:
        return {
            "ok": False,
            "error": detail,
        }

    state = load_state()

    if task.task_id not in state["bridge_tasks"]:
        state["bridge_tasks"].append(task.task_id)

    save_state(state)

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
