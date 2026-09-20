from __future__ import annotations

import importlib.util
import json
import re
import secrets
import subprocess
import sys
import threading
import time
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


def load_ai_transport():
    path = ROOT / "control/hourly/ai_transport.py"
    spec = importlib.util.spec_from_file_location(
        "prediction_research_ai_transport",
        path,
    )

    if spec is None or spec.loader is None:
        raise ImportError(
            f"cannot load AI transport from {path}"
        )

    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod

    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.modules.pop(spec.name, None)
        raise

    return mod


AI_TRANSPORT = load_ai_transport()

def load_work_cadence():
    path = ROOT / 'control/hourly/work_cadence.py'
    spec = importlib.util.spec_from_file_location(
        'prediction_research_work_cadence',
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



TASK_ID_RE = re.compile(
    r"^[A-Za-z0-9_.:-]{3,160}$"
)


def discover(task_id: str) -> dict:
    if not TASK_ID_RE.fullmatch(task_id):
        return {
            "ok": False,
            "error": "invalid task_id",
        }

    lifecycle_update(
        task_id,
        "DISCOVERED",
        "browser discovered task marker",
    )

    return {
        "ok": True,
        "task_id": task_id,
        "state": "DISCOVERED",
    }


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

            lifecycle_update(
                task.task_id,
                "ACCEPTED",
                "bridge accepted idempotent enqueue",
            )

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

        cadence_result = WORK_CADENCE.check(
            reason=f'bridge_task:{task.task_id}',
        )
        if not cadence_result.get('allowed'):
            reason = str(cadence_result.get('reason', 'CADENCE_BLOCKED'))
            lifecycle_update(
                task.task_id,
                'FAILED',
                'bridge blocked by work cadence: ' + reason,
            )
            return {
                'ok': False,
                'error': 'work cadence blocked',
                'reason': reason,
                'cadence': cadence_result,
                'queue_status': queue_status(),
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

    prefer_incident = bool(
        state.get("outbox_prefer_incident", False)
    )
    has_pending_result = any(
        (
            task_id not in acked
            and (RESULTS / task_id / "RESULT.json").exists()
        )
        for task_id in bridge_tasks
    )


    # RELIABILITY-E056: deliver local watchdog incidents
    # through the already proven browser result outbox.
    incident_dir = (
        Path.home()
        / ".local"
        / "state"
        / "prediction-research"
        / "incidents"
    )

    if incident_dir.exists() and (
        prefer_incident or not has_pending_result
    ):
        incident_paths = sorted(
            incident_dir.glob("*.json"),
            key=lambda path: path.stat().st_mtime,
        )

        for incident_path in incident_paths:
            try:
                incident = json.loads(
                    incident_path.read_text(
                        encoding="utf-8"
                    )
                )
            except Exception:
                continue

            if not incident.get("deliver_to_chat"):
                continue

            # Hourly research wakes have a dedicated AI-only
            # transport. Never expose them as ordinary executor
            # result messages as well.
            if (
                incident.get("reason")
                == "HOURLY_RESEARCH_WAKE"
            ):
                continue

            raw_task_id = (
                "INCIDENT-"
                + incident_path.stem
            )

            task_id = "".join(
                ch
                if (
                    ch.isalnum()
                    or ch in "._:-"
                )
                else "_"
                for ch in raw_task_id
            )[:150]

            if task_id in acked:
                continue

            bridge_tasks = state.setdefault(
                "bridge_tasks",
                [],
            )

            if task_id not in bridge_tasks:
                bridge_tasks.append(task_id)
                save_state(state)

            head = git(
                "rev-parse",
                "--short",
                "HEAD",
            ).stdout.strip()

            result = {
                "task_id": task_id,
                "hypothesis_id":
                    "CONTROL-NO-SILENT-WAITING",
                "task_class": "infrastructure",
                "status": "incident",
                "source_commit": head,
                "started_at": None,
                "finished_at": None,
                "exit_code": None,
                "command": [],
                "incident": incident,
            }

            state["outbox_prefer_incident"] = False
            save_state(state)

            return {
                "task_id": task_id,
                "result": result,
                "stdout": json.dumps(
                    incident,
                    indent=2,
                    sort_keys=True,
                ),
                "stderr": "",
                "git_head": head,
            }

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

        state["outbox_prefer_incident"] = True
        save_state(state)

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


def _control_continue_result(task_id: str) -> dict | None:
    result_file = RESULTS / task_id / "RESULT.json"
    if not result_file.exists():
        return None
    try:
        result = json.loads(result_file.read_text(encoding="utf-8"))
    except Exception:
        return None
    if result.get("status") not in {"completed", "failed"}:
        return None
    if result.get("task_class") not in {"research", "infrastructure"}:
        return None
    return result


def _control_continue_item(source_task_id: str, reason: str) -> dict | None:
    result = _control_continue_result(source_task_id)
    if result is None:
        return None

    safe_source = "".join(
        ch if (ch.isalnum() or ch in "._:-") else "_"
        for ch in source_task_id
    )[:120]
    wake_id = ("control-continue-" + safe_source)[:150]

    return {
        "kind": "AI_WORK_BUNDLE",
        "schema": "PVA_CONTROL_CONTINUE_V1",
        "task_id": wake_id,
        "run_id": "control-" + safe_source,
        "bundle_ref": "control/results/" + source_task_id + "/RESULT.json",
        "bundle": {
            "schema": "PVA_CONTROL_CONTINUE_BUNDLE_V1",
            "source_task_id": source_task_id,
            "source_result": {
                "status": result.get("status"),
                "task_class": result.get("task_class"),
                "hypothesis_id": result.get("hypothesis_id"),
                "exit_code": result.get("exit_code"),
                "source_commit": result.get("source_commit"),
            },
            "wake_reason": reason,
            "continuation_policy": {
                "do_not_wait_for_manual_continue": True,
                "inspect_source_of_truth_first": True,
                "advance_after_pass": True,
                "diagnose_and_repair_after_failure": True,
                "respect_work_cadence": True,
                "no_live_trading": True,
                "no_paid_actions": True,
                "no_wallet_actions": True,
                "no_openai_api": True,
            },
        },
        "response_contract": {
            "schema": "PVA_CONTROL_CONTINUE_RESPONSE_V1",
            "direct_execution_allowed": False,
            "economic_conclusion": "NO_PROVEN_EDGE",
        },
        "instruction": (
            "Continue the currently authorized Prediction research and control-plane work "
            "autonomously from this completed bridge result. Inspect the returned result "
            "and repository state first. If it passed, advance to the next planned gate "
            "or research task. If it failed, diagnose and repair it. Do not stop merely "
            "to wait for the user to say continue. If a work-cadence cooldown or an "
            "authorization boundary blocks further work, report that instead. Never "
            "perform live trading, paid actions, wallet actions or OpenAI API calls."
        ),
        "guardrails": {
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "openai_api": False,
            "direct_executor_route": False,
        },
    }


def _queue_control_continue(state: dict, source_task_id: str, reason: str) -> bool:
    seen = state.setdefault("control_continue_seen", [])
    if source_task_id in seen:
        return False

    item = _control_continue_item(source_task_id, reason)
    if item is None:
        return False

    queue = state.setdefault("control_continue_queue", [])
    queue.append(item)
    seen.append(source_task_id)

    while len(queue) > 100:
        queue.pop(0)
    while len(seen) > 500:
        seen.pop(0)
    return True


def _sync_recent_ack_stall_fallbacks(state: dict) -> bool:
    incident_dir = Path.home() / ".local" / "state" / "prediction-research" / "incidents"
    if not incident_dir.exists():
        return False

    paths = sorted(
        incident_dir.glob("*__CHAT_ACK_STALL.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )[:1]
    if not paths:
        return False

    try:
        incident = json.loads(paths[0].read_text(encoding="utf-8"))
    except Exception:
        return False

    if incident.get("reason") != "CHAT_ACK_STALL":
        return False

    last_seen = float(incident.get("last_seen_at") or incident.get("first_seen_at") or 0)
    if last_seen and time.time() - last_seen > 1800:
        return False

    source_task_id = str(incident.get("task_id") or "")
    if not source_task_id:
        return False

    return _queue_control_continue(state, source_task_id, "CHAT_ACK_STALL_FALLBACK")


def _next_control_continue_item(state: dict, ai_acked: set[str]) -> dict | None:
    for item in state.get("control_continue_queue", []):
        if not isinstance(item, dict):
            continue
        task_id = str(item.get("task_id") or "")
        if not task_id or task_id in ai_acked:
            continue
        return item
    return None

def next_ai_outbox_item() -> dict | None:
    state = load_state()
    ai_acked = set(state.get("ai_acked", []))

    if _sync_recent_ack_stall_fallbacks(state):
        save_state(state)

    control_item = _next_control_continue_item(state, ai_acked)
    if control_item is not None:
        return control_item

    incident_dir = (
        Path.home()
        / ".local"
        / "state"
        / "prediction-research"
        / "incidents"
    )

    if not incident_dir.exists():
        return None

    incident_paths = sorted(
        incident_dir.glob(
            "*__HOURLY_RESEARCH_WAKE.json"
        ),
        key=lambda path: path.stat().st_mtime,
    )

    # Prefer newest valid hourly bundle.
    for incident_path in reversed(incident_paths):
        try:
            incident = json.loads(
                incident_path.read_text(
                    encoding="utf-8"
                )
            )
        except Exception:
            continue

        task_id = str(
            incident.get("task_id") or ""
        )

        if not task_id or task_id in ai_acked:
            continue

        if not AI_TRANSPORT.should_offer_ai_work(
            incident
        ):
            continue

        try:
            item = AI_TRANSPORT.build_chat_item(
                incident
            )
        except Exception:
            continue

        # Explicitly fail closed against accidental executor
        # semantics.
        forbidden = {
            "command",
            "shell",
            "argv",
            "exec",
            "executable",
        }

        if forbidden.intersection(item):
            continue

        if item.get("kind") != "AI_WORK_BUNDLE":
            continue

        guardrails = item.get("guardrails") or {}

        if (
            guardrails.get("direct_executor_route")
            is not False
        ):
            continue

        return item

    return None


def acknowledge_ai(task_id: str) -> dict:
    state = load_state()

    item = next_ai_outbox_item()

    if (
        not item
        or item.get("task_id") != task_id
    ):
        if task_id in set(
            state.get("ai_acked", [])
        ):
            return {
                "ok": True,
                "task_id": task_id,
                "already_acked": True,
            }

        return {
            "ok": False,
            "error": "unknown AI work item",
        }

    ai_acked = state.setdefault(
        "ai_acked",
        [],
    )

    if task_id not in ai_acked:
        ai_acked.append(task_id)

    save_state(state)

    return {
        "ok": True,
        "task_id": task_id,
    }


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

    _queue_control_continue(state, task_id, "RESULT_ACKED")

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

        if path == "/ai-outbox":
            self.send_json(
                200,
                {
                    "item": next_ai_outbox_item()
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
                if path == "/incident":
                    reason = str(
                        payload.get(
                            "reason",
                            "BROWSER_INCIDENT",
                        )
                    )[:80]

                    detail = str(
                        payload.get(
                            "detail",
                            "",
                        )
                    )[:4000]

                    incident_id = str(
                        payload.get(
                            "incident_id",
                            "browser-incident",
                        )
                    )[:160]

                    safe_id = re.sub(
                        r"[^A-Za-z0-9_.:-]+",
                        "_",
                        incident_id,
                    )

                    safe_reason = re.sub(
                        r"[^A-Za-z0-9_.:-]+",
                        "_",
                        reason,
                    )

                    incident_dir = (
                        Path.home()
                        / ".local"
                        / "state"
                        / "prediction-research"
                        / "incidents"
                    )

                    incident_dir.mkdir(
                        parents=True,
                        exist_ok=True,
                    )

                    now = time.time()

                    incident_path = (
                        incident_dir
                        / (
                            safe_id
                            + "__"
                            + safe_reason
                            + ".json"
                        )
                    )

                    if incident_path.exists():
                        try:
                            data = json.loads(
                                incident_path.read_text(
                                    encoding="utf-8"
                                )
                            )
                        except Exception:
                            data = {}
                    else:
                        data = {}

                    data.update(
                        {
                            "incident_id": incident_id,
                            "task_id": safe_id,
                            "reason": reason,
                            "detail": detail,
                            "status": "OPEN",
                            "deliver_to_chat": True,
                            "first_seen_at":
                                data.get(
                                    "first_seen_at",
                                    now,
                                ),
                            "last_seen_at": now,
                            "automatic_action": "NONE",
                            "running_task_killed": False,
                            "paid_action": False,
                            "live_trading_action": False,
                            "wallet_action": False,
                        }
                    )

                    incident_path.write_text(
                        json.dumps(
                            data,
                            indent=2,
                            sort_keys=True,
                        )
                        + chr(10),
                        encoding="utf-8",
                    )

                    self.send_json(
                        200,
                        {
                            "ok": True,
                            "incident_id":
                                incident_id,
                        },
                    )
                    return

                if path == "/discover":
                    task_id = str(
                        payload.get("task_id", "")
                    )

                    result = discover(task_id)

                    self.send_json(
                        200 if result.get("ok") else 400,
                        result,
                    )
                    return

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

                if path == "/ai-ack":
                    task_id = str(payload.get("task_id", ""))
                    result = acknowledge_ai(task_id)

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
