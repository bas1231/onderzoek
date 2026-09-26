"""Build safe, fail-closed Control Room snapshots from local Research-OS evidence.

Input: repository files, runtime JSON evidence, Git metadata and local host metrics.
Output: a JSON-serializable read-only snapshot for the dashboard.
Non-goals: executing tasks, changing project state, network polling, or reading secrets.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SNAPSHOT_SCHEMA = "PREDICTION_CONTROL_ROOM_V0"
MAX_JSON_BYTES = 512 * 1024
MAX_TASKS = 80
MAX_ACTIVITY = 40

RUNTIME_ROOTS = (
    "control/lifecycle",
    "control/results",
    "control/jobs",
    "knowledge/ai_exchange/requests",
    "knowledge/ai_exchange/responses",
    "knowledge/runs",
    "hourly-reports",
)

SAFE_TASK_FIELDS = (
    "task_id",
    "hypothesis_id",
    "task_class",
    "operation",
    "status",
    "state",
    "source_commit",
    "started_at",
    "finished_at",
    "exit_code",
    "consumer_id",
    "agent",
    "role",
    "capability",
)

SECRET_KEY_RE = re.compile(
    r"(?:secret|password|passwd|token|api[_-]?key|private[_-]?key|credential|authorization|cookie)",
    re.IGNORECASE,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso_from_epoch(value: float | int | None) -> str | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def _safe_json(path: Path) -> tuple[Any | None, str | None]:
    """Read a small JSON file without following unbounded content."""
    try:
        stat = path.stat()
        if stat.st_size > MAX_JSON_BYTES:
            return None, "too_large"
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle), None
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, type(exc).__name__


def _run_git(root: Path, *args: str, timeout: float = 2.0) -> tuple[int, str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return result.returncode, result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return 127, ""


def _git_snapshot(root: Path) -> dict[str, Any]:
    inside_rc, inside = _run_git(root, "rev-parse", "--is-inside-work-tree")
    if inside_rc != 0 or inside != "true":
        return {
            "status": "UNKNOWN",
            "reason": "not_a_git_worktree",
            "branch": None,
            "head": None,
            "dirty": None,
            "changes": [],
            "ahead": None,
            "behind": None,
            "recent_commits": [],
        }

    _, branch = _run_git(root, "branch", "--show-current")
    _, head = _run_git(root, "rev-parse", "--short=12", "HEAD")
    status_rc, porcelain = _run_git(root, "status", "--porcelain=v1", "--untracked-files=normal")
    changes = [line[:160] for line in porcelain.splitlines() if line.strip()] if status_rc == 0 else []

    ahead = behind = None
    div_rc, divergence = _run_git(root, "rev-list", "--left-right", "--count", "HEAD...@{upstream}")
    if div_rc == 0:
        try:
            ahead_s, behind_s = divergence.split()
            ahead, behind = int(ahead_s), int(behind_s)
        except (ValueError, TypeError):
            pass

    log_rc, log_text = _run_git(
        root,
        "log",
        "-n",
        "12",
        "--date=iso-strict",
        "--pretty=format:%H%x1f%cI%x1f%s",
    )
    commits: list[dict[str, Any]] = []
    if log_rc == 0:
        for line in log_text.splitlines():
            parts = line.split("\x1f", 2)
            if len(parts) == 3:
                commits.append({"sha": parts[0][:12], "at": parts[1], "message": parts[2][:240]})

    return {
        "status": "HEALTHY" if status_rc == 0 else "UNKNOWN",
        "branch": branch or None,
        "head": head or None,
        "dirty": bool(changes) if status_rc == 0 else None,
        "changes": changes[:30],
        "ahead": ahead,
        "behind": behind,
        "recent_commits": commits,
    }


def _extract_economic_status(root: Path, registry: dict[str, Any] | None) -> tuple[str, str]:
    overview = root / "PROJECT_IN_EEN_OOGOPSLAG.md"
    try:
        text = overview.read_text(encoding="utf-8")[:20_000]
    except (OSError, UnicodeError):
        text = ""
    patterns = (
        r"Huidige economische status:\s*\*\*([A-Z0-9_ -]+)\*\*",
        r"economic(?:al)? status[^A-Z0-9_]+([A-Z][A-Z0-9_ -]{2,})",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip().upper().replace(" ", "_"), "PROJECT_IN_EEN_OOGOPSLAG.md"
    if registry and isinstance(registry.get("valid_null_result"), str):
        return registry["valid_null_result"], "agents/registry.json:valid_null_result"
    return "UNKNOWN", "missing_evidence"


def _project_snapshot(root: Path) -> tuple[dict[str, Any], dict[str, Any] | None, list[str]]:
    registry_path = root / "agents" / "registry.json"
    registry_raw, error = _safe_json(registry_path)
    registry = registry_raw if isinstance(registry_raw, dict) else None
    parse_errors = [f"agents/registry.json:{error}"] if error else []
    economic_status, source = _extract_economic_status(root, registry)

    def safety_value(key: str) -> bool | None:
        value = registry.get(key) if registry else None
        return value if isinstance(value, bool) else None

    return (
        {
            "economic_status": economic_status,
            "economic_status_source": source,
            "live_trading": safety_value("live_trading"),
            "paid_actions": safety_value("paid_actions"),
            "wallet_actions": safety_value("wallet_actions"),
            "registry_version": registry.get("version") if registry else None,
            "default_status": registry.get("default_status") if registry else None,
        },
        registry,
        parse_errors,
    )


def _walk_json_files(root: Path, relative_roots: Iterable[str]) -> Iterable[Path]:
    for rel in relative_roots:
        base = root / rel
        if not base.exists() or not base.is_dir():
            continue
        try:
            for path in base.rglob("*.json"):
                if path.is_file():
                    yield path
        except OSError:
            continue


def _safe_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        if isinstance(value, str):
            return value[:300]
        return value
    return None


def _pick_safe_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """Select metadata only; arbitrary payload values are intentionally ignored."""
    result: dict[str, Any] = {}
    candidates: list[dict[str, Any]] = [payload]
    for key in ("task", "result"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            candidates.append(nested)

    for candidate in candidates:
        for key in SAFE_TASK_FIELDS:
            if key in result or key not in candidate or SECRET_KEY_RE.search(key):
                continue
            safe = _safe_value(candidate.get(key))
            if safe is not None:
                result[key] = safe

    for key in ("updated_at", "created_at"):
        if key in payload and isinstance(payload[key], (int, float, str)):
            result[key] = payload[key]

    history = payload.get("history")
    if isinstance(history, list) and history:
        last = history[-1]
        if isinstance(last, dict):
            state = last.get("state")
            at = last.get("at")
            if isinstance(state, str):
                result["last_transition"] = state[:100]
            if isinstance(at, (int, float, str)):
                result["last_transition_at"] = at
    return result


def _event_time(meta: dict[str, Any], mtime: float) -> tuple[float, str]:
    for key in ("finished_at", "updated_at", "last_transition_at", "started_at", "created_at"):
        value = meta.get(key)
        if isinstance(value, (int, float)):
            return float(value), _iso_from_epoch(value) or _iso_from_epoch(mtime) or _now_iso()
        if isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return dt.timestamp(), dt.astimezone(timezone.utc).isoformat()
            except ValueError:
                continue
    return mtime, _iso_from_epoch(mtime) or _now_iso()


def _task_snapshot(root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    tasks: list[dict[str, Any]] = []
    errors: list[str] = []
    for path in _walk_json_files(root, RUNTIME_ROOTS):
        payload, error = _safe_json(path)
        rel = path.relative_to(root).as_posix()
        if error:
            errors.append(f"{rel}:{error}")
            continue
        if not isinstance(payload, dict):
            continue
        meta = _pick_safe_fields(payload)
        if not meta.get("task_id") and not any(k in meta for k in ("status", "state", "operation", "hypothesis_id")):
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            mtime = 0.0
        ts, at = _event_time(meta, mtime)
        tasks.append({"source": rel, "at": at, "_sort": ts, **meta})
    tasks.sort(key=lambda item: item["_sort"], reverse=True)
    for task in tasks:
        task.pop("_sort", None)
    return tasks[:MAX_TASKS], errors[:50]


def _agent_snapshot(registry: dict[str, Any] | None, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not registry:
        return []
    raw_roles: list[dict[str, Any]] = []
    for key in ("roles", "transient_roles"):
        value = registry.get(key)
        if isinstance(value, list):
            raw_roles.extend(item for item in value if isinstance(item, dict))

    agents: list[dict[str, Any]] = []
    for role in raw_roles:
        role_id = str(role.get("id") or "unknown")
        capabilities = [str(item) for item in role.get("capabilities", []) if isinstance(item, str)]
        needles = {role_id.lower(), *(cap.lower() for cap in capabilities)}
        matches: list[dict[str, Any]] = []
        for task in tasks:
            haystack = " ".join(
                str(task.get(key, ""))
                for key in ("agent", "role", "capability", "task_class", "operation", "source")
            ).lower()
            if any(needle and needle in haystack for needle in needles):
                matches.append(task)
        latest = matches[0] if matches else None
        agents.append(
            {
                "id": role_id,
                "authority": role.get("authority"),
                "purpose": str(role.get("purpose") or "")[:400],
                "capabilities": capabilities,
                "runtime_status": "EVIDENCE_SEEN" if latest else "UNKNOWN_NO_HEARTBEAT",
                "last_seen": latest.get("at") if latest else None,
                "last_task_id": latest.get("task_id") if latest else None,
                "last_state": (latest.get("status") or latest.get("state") or latest.get("last_transition")) if latest else None,
            }
        )
    return agents


def _resource_snapshot(root: Path) -> dict[str, Any]:
    cpu_count = os.cpu_count()
    try:
        load = list(os.getloadavg())
    except (OSError, AttributeError):
        load = None

    memory: dict[str, Any] = {"total_bytes": None, "available_bytes": None, "used_percent": None}
    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        values: dict[str, int] = {}
        try:
            for line in meminfo.read_text(encoding="utf-8").splitlines():
                key, raw = line.split(":", 1)
                number = raw.strip().split()[0]
                values[key] = int(number) * 1024
            total = values.get("MemTotal")
            available = values.get("MemAvailable")
            used_percent = round((1 - (available / total)) * 100, 1) if total and available is not None else None
            memory = {"total_bytes": total, "available_bytes": available, "used_percent": used_percent}
        except (OSError, UnicodeError, ValueError, ZeroDivisionError):
            pass

    try:
        disk = shutil.disk_usage(root)
        disk_info = {
            "total_bytes": disk.total,
            "free_bytes": disk.free,
            "used_percent": round((disk.used / disk.total) * 100, 1) if disk.total else None,
        }
    except OSError:
        disk_info = {"total_bytes": None, "free_bytes": None, "used_percent": None}

    uptime_seconds = None
    try:
        uptime_seconds = float(Path("/proc/uptime").read_text(encoding="utf-8").split()[0])
    except (OSError, UnicodeError, ValueError, IndexError):
        pass

    return {
        "cpu_count": cpu_count,
        "load_1_5_15": load,
        "memory": memory,
        "disk": disk_info,
        "uptime_seconds": uptime_seconds,
    }


def _provenance(root: Path) -> list[dict[str, Any]]:
    paths = ["agents/registry.json", "PROJECT_IN_EEN_OOGOPSLAG.md", *RUNTIME_ROOTS]
    result: list[dict[str, Any]] = []
    for rel in paths:
        path = root / rel
        exists = path.exists()
        mtime = None
        if exists:
            try:
                mtime = _iso_from_epoch(path.stat().st_mtime)
            except OSError:
                pass
        result.append({"path": rel, "exists": exists, "mtime": mtime})
    return result


def _alerts(project: dict[str, Any], git: dict[str, Any], tasks: list[dict[str, Any]], parse_errors: list[str], agents: list[dict[str, Any]]) -> list[dict[str, str]]:
    alerts: list[dict[str, str]] = []
    for key, label in (("live_trading", "Live trading"), ("paid_actions", "Paid actions"), ("wallet_actions", "Wallet actions")):
        value = project.get(key)
        if value is True:
            alerts.append({"severity": "CRITICAL", "code": f"{key.upper()}_ENABLED", "message": f"{label} staat TRUE in agents/registry.json."})
        elif value is None:
            alerts.append({"severity": "WARNING", "code": f"{key.upper()}_UNKNOWN", "message": f"{label}-evidence ontbreekt; status blijft UNKNOWN."})

    if project.get("economic_status") == "UNKNOWN":
        alerts.append({"severity": "WARNING", "code": "ECONOMIC_STATUS_UNKNOWN", "message": "Economische projectstatus kon niet veilig worden vastgesteld."})
    if git.get("status") == "UNKNOWN":
        alerts.append({"severity": "WARNING", "code": "GIT_UNKNOWN", "message": "Git-status kon niet worden vastgesteld."})
    elif git.get("dirty"):
        alerts.append({"severity": "WARNING", "code": "GIT_DIRTY", "message": f"Werkboom bevat {len(git.get('changes') or [])} zichtbare wijziging(en)."})
    if parse_errors:
        alerts.append({"severity": "WARNING", "code": "PARSE_ERRORS", "message": f"{len(parse_errors)} lokaal(e) evidencebestand(en) konden niet veilig worden gelezen."})
    if not tasks:
        alerts.append({"severity": "WARNING", "code": "NO_RUNTIME_EVIDENCE", "message": "Geen recente lokale task/result/lifecycle JSON-evidence gevonden in de bekende runtimepaden."})
    unknown_agents = sum(1 for agent in agents if agent.get("runtime_status") == "UNKNOWN_NO_HEARTBEAT")
    if unknown_agents:
        alerts.append({"severity": "INFO", "code": "AGENT_HEARTBEAT_UNKNOWN", "message": f"Voor {unknown_agents} geregistreerde agentgroep(en) is geen expliciete heartbeat-evidence gevonden; dit betekent niet dat ze defect zijn."})
    return alerts


def _activity(git: dict[str, Any], tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for task in tasks[:25]:
        events.append(
            {
                "at": task.get("at"),
                "kind": "TASK",
                "title": task.get("task_id") or task.get("operation") or "runtime evidence",
                "status": task.get("status") or task.get("state") or task.get("last_transition") or "UNKNOWN",
                "source": task.get("source"),
            }
        )
    for commit in git.get("recent_commits") or []:
        events.append({"at": commit.get("at"), "kind": "GIT", "title": commit.get("message"), "status": commit.get("sha"), "source": "git log"})

    def sort_key(event: dict[str, Any]) -> float:
        raw = event.get("at")
        if not isinstance(raw, str):
            return 0.0
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return 0.0

    events.sort(key=sort_key, reverse=True)
    return events[:MAX_ACTIVITY]


def build_snapshot(repo_root: str | os.PathLike[str]) -> dict[str, Any]:
    """Return one complete Control Room snapshot without mutating the repository."""
    root = Path(repo_root).expanduser().resolve()
    project, registry, errors = _project_snapshot(root)
    tasks, task_errors = _task_snapshot(root)
    errors.extend(task_errors)
    git = _git_snapshot(root)
    agents = _agent_snapshot(registry, tasks)
    alerts = _alerts(project, git, tasks, errors, agents)
    return {
        "schema": SNAPSHOT_SCHEMA,
        "generated_at": _now_iso(),
        "dashboard": {
            "read_only": True,
            "bind_default": "127.0.0.1",
            "outbound_network_calls": False,
            "mutation_endpoints": False,
        },
        "project": project,
        "system_health": {
            "status": "CRITICAL" if any(a["severity"] == "CRITICAL" for a in alerts) else ("WARNING" if any(a["severity"] == "WARNING" for a in alerts) else "HEALTHY"),
            "parse_error_count": len(errors),
        },
        "git": git,
        "agents": agents,
        "tasks": tasks,
        "activity": _activity(git, tasks),
        "alerts": alerts,
        "resources": _resource_snapshot(root),
        "provenance": _provenance(root),
    }
