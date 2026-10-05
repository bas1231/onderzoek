from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import statistics
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

SCHEMA = "PREDICTION_CONTROL_CENTER_SNAPSHOT_V1"
REVIVE_SCHEMA = "PREDICTION_RESEARCH_REVIVE_REQUEST_V1"
MAX_ARTIFACT_BYTES = 2_000_000
MAX_JSON_BYTES = 4_000_000
CACHE_SECONDS = 3.0

TERMINAL_FAILURES = {
    "FAIL", "FAILED", "ERROR", "INCIDENT", "REJECTED", "AMBIGUOUS",
    "BLOCKED", "BLOCKED_ROUTE", "TASK_PARSE_FAILURE",
}
SUCCESS_STATES = {"PASS", "COMPLETED", "DONE", "SUCCESS", "SENT"}
ACTIVE_STATES = {
    "RUNNING", "STARTED", "CLAIMED", "INFLIGHT",
    "CONTINUE_QUEUED", "PENDING",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def safe_json(path: Path):
    try:
        if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_JSON_BYTES:
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def parse_time(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def compact_text(value, limit=180):
    if value is None:
        return ""
    text = " ".join(str(value).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def nested_find(obj, key):
    found = []
    if isinstance(obj, dict):
        if key in obj:
            found.append(obj[key])
        for value in obj.values():
            found.extend(nested_find(value, key))
    elif isinstance(obj, list):
        for value in obj:
            found.extend(nested_find(value, key))
    return found


def status_of(obj):
    if not isinstance(obj, dict):
        return "UNKNOWN"
    for key in ("status", "state", "queue_status", "decision"):
        value = obj.get(key)
        if isinstance(value, str) and value:
            return value.upper()
    result = obj.get("result")
    if isinstance(result, dict):
        return status_of(result)
    return "UNKNOWN"


def percentile(values, p):
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    idx = (len(ordered) - 1) * p
    low = int(idx)
    high = min(low + 1, len(ordered) - 1)
    frac = idx - low
    return ordered[low] * (1 - frac) + ordered[high] * frac


class ControlCenterModel:
    def __init__(self, repo: Path, state_root: Path | None = None):
        self.repo = repo.expanduser().resolve()
        self.state_root = (
            state_root.expanduser().resolve()
            if state_root
            else (Path.home() / ".local/state/prediction-project-executor/control-center").resolve()
        )
        self.revive_root = self.state_root / "revive_requests"
        self.command_state = (Path.home() / ".local/state/prediction-command-bus/tasks").resolve()
        self.executor_state = (Path.home() / ".local/state/prediction-project-executor").resolve()
        self.mirror_root = (Path.home() / ".local/share/prediction-project-executor/repo").resolve()
        self._cache_lock = threading.Lock()
        self._cache_at = 0.0
        self._cache = None

    def invalidate(self):
        with self._cache_lock:
            self._cache_at = 0.0
            self._cache = None

    def _candidate_files(self):
        root = self.repo / "knowledge/candidates"
        return sorted(root.glob("*.json")) if root.is_dir() else []

    def _manual_seed_files(self):
        root = self.repo / "knowledge/manual_scout_seeds"
        return sorted(root.glob("*.md")) if root.is_dir() else []

    def _research_artifacts(self):
        roots = [
            self.repo / "knowledge/research",
            self.repo / "knowledge/public_research",
            self.repo / "knowledge/strategy_benchmarks",
        ]
        rows = []
        for root in roots:
            if not root.is_dir():
                continue
            for path in sorted(root.glob("*.md")):
                rel = str(path.relative_to(self.repo))
                rows.append({
                    "id": "LEGACY-ARTIFACT-" + hashlib.sha256(rel.encode()).hexdigest()[:14],
                    "name": path.stem,
                    "path": rel,
                    "kind": "legacy_research_artifact",
                    "updated_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                })
        return rows

    def _normalize_candidate(self, obj, path):
        candidate_id = str(obj.get("candidate_id") or path.stem)
        hypothesis = obj.get("hypothesis") or obj.get("mechanism") or obj.get("open_question") or candidate_id
        queue = str(obj.get("queue_status") or "UNKNOWN")
        decision = str(obj.get("decision") or obj.get("scientific_status") or "UNPROVEN")
        phase = str(obj.get("phase") or "UNKNOWN")
        created = obj.get("created_at") or obj.get("queue_entered_at")
        updated = obj.get("updated_at") or created
        gates = obj.get("gates") if isinstance(obj.get("gates"), dict) else {}
        refs = []
        for key in ("evidence_refs", "scout_evidence_refs", "prospective_protocols"):
            value = obj.get(key)
            if isinstance(value, list):
                refs.extend(str(x) for x in value if isinstance(x, str))
        for key in ("manual_seed_ref", "build_result_ref", "measurement_result_ref"):
            if isinstance(obj.get(key), str):
                refs.append(obj[key])
        return {
            "candidate_id": candidate_id,
            "title": compact_text(hypothesis, 120),
            "hypothesis": str(hypothesis),
            "mechanism": str(obj.get("mechanism") or ""),
            "open_question": str(obj.get("open_question") or ""),
            "next_decisive_test": str(obj.get("next_decisive_test") or ""),
            "lane": str(obj.get("lane") or "unknown"),
            "priority": str(obj.get("priority") or ""),
            "phase": phase,
            "queue_status": queue,
            "decision": decision,
            "scientific_status": str(obj.get("scientific_status") or decision),
            "created_at": created,
            "updated_at": updated,
            "provenance": str(obj.get("provenance") or "LEGACY_OR_CANONICAL"),
            "source_path": str(path.relative_to(self.repo)),
            "evidence_refs": sorted(set(refs)),
            "active_experiment_ids": obj.get("active_experiment_ids") if isinstance(obj.get("active_experiment_ids"), list) else [],
            "gates": gates,
            "resume_condition": obj.get("resume_condition"),
            "resurrection_condition": obj.get("resurrection_condition"),
            "stop_condition": obj.get("stop_condition"),
            "qualification_fixture": bool(obj.get("qualification_fixture")),
            "safety": {
                "live_trading": bool(obj.get("live_trading")),
                "paid_actions": bool(obj.get("paid_actions")),
                "wallet_actions": bool(obj.get("wallet_actions")),
            },
            "raw": obj,
            "legacy_imported": False,
        }

    def load_candidates(self):
        candidates = []
        referenced_seeds = set()
        for path in self._candidate_files():
            obj = safe_json(path)
            if not isinstance(obj, dict):
                continue
            row = self._normalize_candidate(obj, path)
            candidates.append(row)
            ref = obj.get("manual_seed_ref")
            if isinstance(ref, str):
                referenced_seeds.add(ref)

        for path in self._manual_seed_files():
            rel = str(path.relative_to(self.repo))
            if rel in referenced_seeds:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            title = next((line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("#")), path.stem)
            cid = "LEGACY-SEED-" + hashlib.sha256(rel.encode()).hexdigest()[:14]
            candidates.append({
                "candidate_id": cid,
                "title": compact_text(title, 120),
                "hypothesis": compact_text(text, 900),
                "mechanism": "",
                "open_question": "",
                "next_decisive_test": "Herbeoordelen via de actuele governed lifecycle indien gewenst.",
                "lane": "legacy_manual_seed",
                "priority": "",
                "phase": "DISCOVERED",
                "queue_status": "LEGACY_IMPORTED",
                "decision": "UNPROVEN",
                "scientific_status": "NO_PROVEN_EDGE",
                "created_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                "updated_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                "provenance": "LEGACY_MANUAL_SCOUT_SEED",
                "source_path": rel,
                "evidence_refs": [rel],
                "active_experiment_ids": [],
                "gates": {},
                "resume_condition": None,
                "resurrection_condition": None,
                "stop_condition": None,
                "qualification_fixture": False,
                "safety": {"live_trading": False, "paid_actions": False, "wallet_actions": False},
                "raw": {"source_text_excerpt": compact_text(text, 1600)},
                "legacy_imported": True,
            })
        candidates.sort(key=lambda x: (parse_time(x.get("updated_at")) or 0, x["candidate_id"]), reverse=True)
        return candidates

    def _run_paths(self):
        root = self.repo / "knowledge/runs"
        if not root.is_dir():
            return []
        paths = []
        for path in root.rglob("*.json"):
            try:
                if path.is_file() and not path.is_symlink() and path.stat().st_size <= MAX_JSON_BYTES:
                    paths.append(path)
            except OSError:
                pass
        return sorted(paths)

    def load_runs(self):
        rows = []
        for path in self._run_paths():
            obj = safe_json(path)
            if not isinstance(obj, dict):
                continue
            rel = str(path.relative_to(self.repo))
            run_id = str(obj.get("run_id") or obj.get("task_id") or path.stem)
            candidate_ids = []
            for value in nested_find(obj, "candidate_id"):
                if isinstance(value, str) and value not in candidate_ids:
                    candidate_ids.append(value)
            agents = obj.get("agents") if isinstance(obj.get("agents"), dict) else {}
            if not agents:
                role_results = obj.get("role_results")
                if isinstance(role_results, list):
                    for item in role_results:
                        if isinstance(item, dict) and isinstance(item.get("agent_id"), str):
                            agents[item["agent_id"]] = str(item.get("status") or "UNKNOWN")
            rows.append({
                "run_id": run_id,
                "path": rel,
                "status": status_of(obj),
                "decision": str(obj.get("decision") or obj.get("economic_conclusion") or obj.get("scientific_status") or ""),
                "started_at": obj.get("started_at") or obj.get("created_at") or obj.get("timestamp"),
                "finished_at": obj.get("finished_at") or obj.get("updated_at"),
                "candidate_ids": candidate_ids,
                "agents": agents,
                "source_success_count": obj.get("source_success_count"),
                "source_failure_count": obj.get("source_failure_count"),
                "director_decision": compact_text(obj.get("director_decision"), 400),
                "artifact_count": 1,
            })
        rows.sort(key=lambda x: (parse_time(x.get("started_at")) or 0, x["run_id"]), reverse=True)
        return rows

    def _state_files(self, root):
        if not root.is_dir():
            return []
        out = []
        for path in root.glob("*.json"):
            if path.is_file() and not path.is_symlink():
                out.append(path)
        return sorted(out)

    def load_tasks(self):
        by_id = {}
        for source, root in (("command_bus", self.command_state), ("project_executor", self.executor_state)):
            for path in self._state_files(root):
                obj = safe_json(path)
                if not isinstance(obj, dict):
                    continue
                task_id = str(obj.get("task_id") or path.stem)
                item = by_id.setdefault(task_id, {
                    "task_id": task_id,
                    "sources": {},
                    "route_task_id": None,
                    "status": "UNKNOWN",
                    "started_at": None,
                    "finished_at": None,
                    "exit_code": None,
                    "source_commit": None,
                })
                item["sources"][source] = obj
                route = obj.get("route_task_id")
                if isinstance(route, str):
                    item["route_task_id"] = route
                st = status_of(obj)
                if source == "project_executor" or item["status"] == "UNKNOWN":
                    item["status"] = st
                for key in ("started_at", "created_at", "claimed_at", "claimed_at_utc"):
                    if not item["started_at"] and isinstance(obj.get(key), str):
                        item["started_at"] = obj[key]
                for key in ("finished_at", "completed_at", "updated_at", "finished_at_utc", "completed_at_utc"):
                    if not item["finished_at"] and isinstance(obj.get(key), str):
                        item["finished_at"] = obj[key]
                if isinstance(obj.get("exit_code"), int):
                    item["exit_code"] = obj["exit_code"]
                if isinstance(obj.get("source_commit"), str):
                    item["source_commit"] = obj["source_commit"]
                result = obj.get("result")
                if isinstance(result, dict):
                    if isinstance(result.get("exit_code"), int):
                        item["exit_code"] = result["exit_code"]
                    if isinstance(result.get("status"), str) and source == "project_executor":
                        item["status"] = result["status"].upper()
        rows = list(by_id.values())
        rows.sort(key=lambda x: (parse_time(x.get("started_at")) or 0, x["task_id"]), reverse=True)
        return rows

    def _git_output(self, repo: Path, *args: str):
        if not repo.is_dir():
            return None
        try:
            proc = subprocess.run(
                ["git", "-C", str(repo), *args],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if proc.returncode != 0:
            return None
        return (proc.stdout or "").strip()

    def git_sync_status(self):
        head = self._git_output(self.repo, "rev-parse", "HEAD")
        local_main = self._git_output(self.repo, "rev-parse", "refs/heads/main")
        branch = self._git_output(self.repo, "branch", "--show-current")
        dirty_text = self._git_output(self.repo, "status", "--porcelain=v1")
        dirty = None if dirty_text is None else bool(dirty_text)
        dirty_paths = []
        if dirty_text:
            for line in dirty_text.splitlines():
                value = line[3:].strip() if len(line) > 3 else line.strip()
                if value:
                    dirty_paths.append(value)

        mirror_head = (
            self._git_output(self.mirror_root, "rev-parse", "FETCH_HEAD")
            or self._git_output(self.mirror_root, "rev-parse", "refs/remotes/origin/main")
            or self._git_output(self.mirror_root, "rev-parse", "refs/heads/main")
        )
        fetch_file = self.mirror_root / ".git" / "FETCH_HEAD"
        fetched_at = None
        fetch_age_seconds = None
        try:
            if fetch_file.is_file():
                mtime = fetch_file.stat().st_mtime
                fetched_at = datetime.fromtimestamp(mtime, timezone.utc).isoformat()
                fetch_age_seconds = max(0, int(time.time() - mtime))
        except OSError:
            pass

        issues = []
        status = "GREEN"
        if not head or not local_main:
            status = "UNKNOWN"
            issues.append("Production HEAD of lokale main kon niet worden gelezen.")
        else:
            if head != local_main:
                status = "RED"
                issues.append("Production HEAD wijkt af van lokale main.")
            if dirty is True:
                status = "RED"
                issues.append("Production-worktree bevat niet-vastgelegde wijzigingen.")
            if mirror_head:
                if local_main != mirror_head:
                    status = "RED"
                    issues.append("Lokale main wijkt af van de laatst opgehaalde GitHub-main.")
            elif status != "RED":
                status = "UNKNOWN"
                issues.append("Laatst opgehaalde GitHub-main is niet beschikbaar.")

        if status == "GREEN" and fetch_age_seconds is not None and fetch_age_seconds > 3600:
            status = "AMBER"
            issues.append("GitHub-main is langer dan één uur niet opnieuw opgehaald.")

        return {
            "status": status,
            "production_head": head,
            "local_main": local_main,
            "fetched_github_main": mirror_head,
            "production_branch": branch,
            "dirty": dirty,
            "dirty_paths": dirty_paths[:30],
            "fetched_at": fetched_at,
            "fetch_age_seconds": fetch_age_seconds,
            "issues": issues,
        }

    def _chain_alerts(self, tasks, runs, window_seconds=21600):
        cutoff = time.time() - window_seconds
        alerts = []

        for item in tasks:
            status = str(item.get("status") or "UNKNOWN").upper()
            bad = status in TERMINAL_FAILURES or (
                isinstance(item.get("exit_code"), int) and item["exit_code"] != 0
            )
            if not bad:
                continue
            at = item.get("finished_at") or item.get("started_at")
            when = parse_time(at)
            if when is None or when < cutoff:
                continue
            reason = ""
            for source in ("project_executor", "command_bus"):
                obj = item.get("sources", {}).get(source)
                if not isinstance(obj, dict):
                    continue
                values = (
                    nested_find(obj, "error")
                    + nested_find(obj, "detail")
                    + nested_find(obj, "message")
                )
                reason = next(
                    (compact_text(x, 500) for x in values if isinstance(x, str) and x.strip()),
                    reason,
                )
            alerts.append({
                "kind": "TASK",
                "id": item["task_id"],
                "status": status,
                "at": at,
                "route_task_id": item.get("route_task_id"),
                "reason": reason or "Taak in de keten is mislukt; open Fouten voor details.",
            })

        for run in runs:
            status = str(run.get("status") or "UNKNOWN").upper()
            bad_agents = [
                f"{name}:{value}"
                for name, value in (run.get("agents") or {}).items()
                if str(value).upper() in TERMINAL_FAILURES
            ]
            if status not in TERMINAL_FAILURES and not bad_agents:
                continue
            at = run.get("finished_at") or run.get("started_at")
            when = parse_time(at)
            if when is None or when < cutoff:
                continue
            detail = "Onderzoeksuitvoering is mislukt."
            if bad_agents:
                detail = "Agentfout(en): " + ", ".join(bad_agents[:6])
            alerts.append({
                "kind": "RUN",
                "id": run.get("run_id"),
                "status": status,
                "at": at,
                "route_task_id": None,
                "reason": detail,
            })

        alerts.sort(key=lambda x: parse_time(x.get("at")) or 0, reverse=True)
        return alerts[:20]

    def lifecycle_status(self):
        paths = [
            self.repo / "control/control_center/lifecycle_status.json",
            Path(__file__).resolve().parent / "lifecycle_status.json",
        ]
        for path in paths:
            obj = safe_json(path)
            if isinstance(obj, dict) and isinstance(obj.get("stages"), list):
                return obj
        return {
            "schema": "PREDICTION_CONTROL_CENTER_LIFECYCLE_V1",
            "updated_at": None,
            "full_chain_status": "UNKNOWN",
            "full_chain_label": "Ketenstatus onbekend",
            "next_required": "Controleer de canonieke lifecycle-status in Git.",
            "invariant": "NO_TEST_OR_MEASUREMENT_BEFORE_ASTRA_POSTBUILD_APPROVAL",
            "evidence_refs": [],
            "stages": [],
        }

    def load_revive_requests(self):
        rows = []
        if not self.revive_root.is_dir():
            return rows
        for path in sorted(self.revive_root.glob("*.json")):
            obj = safe_json(path)
            if isinstance(obj, dict):
                rows.append(obj)
        rows.sort(key=lambda x: str(x.get("requested_at") or ""), reverse=True)
        return rows

    def request_revive(self, candidate_id, note=""):
        candidates = {x["candidate_id"]: x for x in self.load_candidates()}
        if candidate_id not in candidates:
            raise KeyError("candidate not found")
        self.revive_root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        request_id = f"REVIVE-{stamp}-{uuid.uuid4().hex[:10]}"
        path = self.revive_root / f"{request_id}.json"
        payload = {
            "schema": REVIVE_SCHEMA,
            "request_id": request_id,
            "original_candidate_id": candidate_id,
            "original_source_path": candidates[candidate_id]["source_path"],
            "requested_at": utc_now(),
            "requested_by": "prediction_control_center",
            "status": "REQUESTED",
            "mode": "FULL_CURRENT_GOVERNED_LIFECYCLE",
            "preserve_history": True,
            "create_new_attempt": True,
            "note": compact_text(note, 1000),
            "safety": {
                "live_trading": False,
                "paid_actions": False,
                "wallet_actions": False,
            },
        }
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        self.invalidate()
        return payload

    def _task_metrics(self, tasks):
        durations = []
        success = 0
        failure = 0
        active = 0
        for item in tasks:
            status = str(item.get("status") or "UNKNOWN").upper()
            if status in SUCCESS_STATES and (item.get("exit_code") in (None, 0)):
                success += 1
            if status in TERMINAL_FAILURES or (isinstance(item.get("exit_code"), int) and item["exit_code"] != 0):
                failure += 1
            if status in ACTIVE_STATES:
                active += 1
            a = parse_time(item.get("started_at"))
            b = parse_time(item.get("finished_at"))
            if a is not None and b is not None and b >= a:
                durations.append(b - a)
        complete = success + failure
        return {
            "success": success,
            "failure": failure,
            "active": active,
            "known_complete": complete,
            "success_rate": round(success / complete, 4) if complete else None,
            "duration_median_seconds": round(statistics.median(durations), 2) if durations else None,
            "duration_p95_seconds": round(percentile(durations, 0.95), 2) if durations else None,
        }

    def _candidate_funnel(self, candidates):
        keys = {
            "discovered": 0,
            "selected_or_director": 0,
            "prebuild_review": 0,
            "built": 0,
            "postbuild_review": 0,
            "measured": 0,
            "edge": 0,
            "no_edge": 0,
            "parked_or_rejected": 0,
        }
        for c in candidates:
            keys["discovered"] += 1
            blob = " ".join([
                str(c.get("phase") or ""), str(c.get("queue_status") or ""),
                str(c.get("decision") or ""), str(c.get("scientific_status") or ""),
                " ".join(f"{k}:{v}" for k, v in c.get("gates", {}).items()),
            ]).upper()
            if any(x in blob for x in ("DIRECTOR", "NEEDS_BUILD", "VALIDATION", "ASTRA_")):
                keys["selected_or_director"] += 1
            if "ASTRA_PREBUILD" in blob or "NEEDS_BUILD" in blob:
                keys["prebuild_review"] += 1
            if any(x in blob for x in ("BUILD", "DEVELOPMENT")):
                keys["built"] += 1
            if "ASTRA_POSTBUILD" in blob:
                keys["postbuild_review"] += 1
            if any(x in blob for x in ("SHADOW", "MEASURE", "RESULT_READY", "HOLDOUT")):
                keys["measured"] += 1
            if c.get("decision", "").upper() == "EDGE" or c.get("scientific_status", "").upper() == "EDGE":
                keys["edge"] += 1
            if c.get("decision", "").upper() == "NO_EDGE" or c.get("scientific_status", "").upper() == "NO_EDGE":
                keys["no_edge"] += 1
            if any(x in blob for x in ("PARK", "REJECT")):
                keys["parked_or_rejected"] += 1
        return keys

    def _errors(self, tasks):
        rows = []
        for item in tasks:
            status = str(item.get("status") or "UNKNOWN").upper()
            bad = status in TERMINAL_FAILURES or (isinstance(item.get("exit_code"), int) and item["exit_code"] != 0)
            if not bad:
                continue
            reason = ""
            for source in ("project_executor", "command_bus"):
                obj = item.get("sources", {}).get(source)
                if not isinstance(obj, dict):
                    continue
                candidates = nested_find(obj, "error") + nested_find(obj, "detail") + nested_find(obj, "message")
                reason = next((compact_text(x, 500) for x in candidates if isinstance(x, str) and x.strip()), reason)
            rows.append({
                "task_id": item["task_id"],
                "status": status,
                "exit_code": item.get("exit_code"),
                "route_task_id": item.get("route_task_id"),
                "started_at": item.get("started_at"),
                "finished_at": item.get("finished_at"),
                "reason": reason or "Geen compacte foutreden gevonden; open raw state voor details.",
            })
        return rows[:100]

    def build_snapshot(self, force=False):
        now = time.monotonic()
        with self._cache_lock:
            if not force and self._cache is not None and now - self._cache_at < CACHE_SECONDS:
                return self._cache

        candidates = self.load_candidates()
        runs = self.load_runs()
        all_tasks = self.load_tasks()
        active_tasks = [
            item for item in all_tasks
            if str(item.get("status") or "").upper() in ACTIVE_STATES
        ]
        revives = self.load_revive_requests()
        lifecycle = self.lifecycle_status()
        git_sync = self.git_sync_status()
        chain_alerts = self._chain_alerts(all_tasks, runs)

        sessions = {}
        for item in active_tasks:
            route = item.get("route_task_id") or "NO_ROUTE_METADATA"
            bucket = sessions.setdefault(
                route,
                {
                    "route_task_id": route,
                    "tasks": 0,
                    "active": 0,
                    "failures": 0,
                    "last_task": None,
                },
            )
            bucket["tasks"] += 1
            bucket["active"] += 1
            if bucket["last_task"] is None:
                bucket["last_task"] = item["task_id"]

        snapshot = {
            "schema": SCHEMA,
            "generated_at": utc_now(),
            "repo": str(self.repo),
            "edge_state": (
                "EDGE"
                if any(c.get("scientific_status", "").upper() == "EDGE" for c in candidates)
                else "NO_PROVEN_EDGE"
            ),
            "safety": {"live_trading": False, "paid_actions": False, "wallet_actions": False},
            "counts": {
                "candidates": len(candidates),
                "runs": len(runs),
                "tasks": len(active_tasks),
                "sessions": len(sessions),
                "revive_requests": len(revives),
                "legacy_candidates": sum(1 for c in candidates if c.get("legacy_imported")),
                "chain_alerts": len(chain_alerts),
            },
            "task_metrics": self._task_metrics(all_tasks),
            "candidate_funnel": self._candidate_funnel(candidates),
            "lifecycle": lifecycle,
            "git_sync": git_sync,
            "chain_alerts": chain_alerts,
            "candidates": candidates,
            "runs": runs,
            "tasks": active_tasks,
            "sessions": sorted(
                sessions.values(),
                key=lambda x: (x["active"], x["tasks"]),
                reverse=True,
            ),
            "errors": self._errors(all_tasks),
            "revive_requests": revives[:100],
            "legacy_artifacts": self._research_artifacts(),
        }
        with self._cache_lock:
            self._cache = snapshot
            self._cache_at = time.monotonic()
        return snapshot

    def candidate_detail(self, candidate_id):
        snapshot = self.build_snapshot()
        candidate = next((x for x in snapshot["candidates"] if x["candidate_id"] == candidate_id), None)
        if candidate is None:
            return None
        linked_runs = [x for x in snapshot["runs"] if candidate_id in x.get("candidate_ids", [])]
        linked_revives = [x for x in snapshot["revive_requests"] if x.get("original_candidate_id") == candidate_id]
        timeline = []
        if candidate.get("created_at"):
            timeline.append({"at": candidate["created_at"], "stage": "DISCOVERY", "status": "CREATED", "detail": candidate.get("provenance")})
        raw = candidate.get("raw") or {}
        director = raw.get("director_trace")
        if isinstance(director, dict):
            timeline.append({
                "at": candidate.get("updated_at"),
                "stage": "DIRECTOR",
                "status": str(director.get("economic_conclusion") or director.get("research_director") or "REVIEWED"),
                "detail": compact_text(director.get("director_decision"), 700),
            })
        for gate, value in candidate.get("gates", {}).items():
            if str(value).upper().startswith("PENDING"):
                continue
            timeline.append({
                "at": candidate.get("updated_at"),
                "stage": gate.upper(),
                "status": str(value),
                "detail": "Gate-state uit candidate-record.",
            })
        for run in linked_runs:
            timeline.append({
                "at": run.get("started_at") or run.get("finished_at"),
                "stage": "RUN",
                "status": run.get("status"),
                "detail": f"{run.get('run_id')} — {run.get('decision') or 'geen eindbesluit'}",
                "path": run.get("path"),
            })
        timeline.sort(key=lambda x: parse_time(x.get("at")) or 0)
        return {
            "candidate": candidate,
            "timeline": timeline,
            "linked_runs": linked_runs,
            "revive_requests": linked_revives,
        }

    def run_detail(self, run_id):
        snapshot = self.build_snapshot()
        run = next((x for x in snapshot["runs"] if x["run_id"] == run_id), None)
        if run is None:
            return None
        path = self.repo / run["path"]
        stem = path.stem
        parent = path.parent
        artifacts = []
        for candidate in sorted(parent.glob(stem + "*"))[:100]:
            if candidate.is_file() and not candidate.is_symlink():
                artifacts.append({
                    "path": str(candidate.relative_to(self.repo)),
                    "size": candidate.stat().st_size,
                    "kind": candidate.suffix.lstrip(".") or "file",
                })
        packet_root = self.repo / "knowledge/runs/agent_packets" / run_id
        if packet_root.is_dir():
            for candidate in sorted(packet_root.rglob("*")):
                if candidate.is_file() and not candidate.is_symlink():
                    artifacts.append({
                        "path": str(candidate.relative_to(self.repo)),
                        "size": candidate.stat().st_size,
                        "kind": "agent_packet",
                    })
                    if len(artifacts) >= 300:
                        break
        return {"run": run, "artifacts": artifacts}

    def artifact(self, rel):
        rel = unquote(rel)
        if not rel or rel.startswith("/") or ".." in Path(rel).parts:
            raise PermissionError("invalid path")
        path = (self.repo / rel).resolve()
        try:
            path.relative_to(self.repo)
        except ValueError:
            raise PermissionError("outside repo")
        if not path.is_file() or path.is_symlink():
            raise FileNotFoundError(rel)
        raw = path.read_bytes()
        truncated = len(raw) > MAX_ARTIFACT_BYTES
        raw = raw[:MAX_ARTIFACT_BYTES]
        return {
            "path": rel,
            "size": path.stat().st_size,
            "truncated": truncated,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path.stat().st_size <= MAX_ARTIFACT_BYTES else None,
            "content": raw.decode("utf-8", errors="replace"),
        }


class Handler(BaseHTTPRequestHandler):
    server_version = "PredictionControlCenter/0.1"

    @property
    def model(self):
        return self.server.model

    @property
    def static_root(self):
        return self.server.static_root

    def log_message(self, fmt, *args):
        print(f"[control-center] {self.address_string()} {fmt % args}", flush=True)

    def _json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _text(self, body, content_type="text/plain; charset=utf-8", status=200):
        raw = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(raw)

    def _static(self, rel):
        if rel in ("", "/"):
            rel = "index.html"
        rel = rel.lstrip("/")
        if ".." in Path(rel).parts:
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        path = (self.static_root / rel).resolve()
        try:
            path.relative_to(self.static_root)
        except ValueError:
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in {"application/javascript", "application/json"}:
            ctype += "; charset=utf-8"
        self._text(path.read_bytes(), ctype)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/snapshot":
            self._json(self.model.build_snapshot())
            return
        if parsed.path.startswith("/api/candidate/"):
            candidate_id = unquote(parsed.path.split("/api/candidate/", 1)[1])
            value = self.model.candidate_detail(candidate_id)
            self._json(value if value is not None else {"error": "not found"}, 200 if value else 404)
            return
        if parsed.path.startswith("/api/run/"):
            run_id = unquote(parsed.path.split("/api/run/", 1)[1])
            value = self.model.run_detail(run_id)
            self._json(value if value is not None else {"error": "not found"}, 200 if value else 404)
            return
        if parsed.path == "/api/artifact":
            query = parse_qs(parsed.query)
            rel = (query.get("path") or [""])[0]
            try:
                self._json(self.model.artifact(rel))
            except PermissionError:
                self._json({"error": "forbidden"}, 403)
            except FileNotFoundError:
                self._json({"error": "not found"}, 404)
            return
        if parsed.path == "/api/health":
            self._json({"status": "PASS", "generated_at": utc_now(), "repo_exists": self.model.repo.is_dir()})
            return
        self._static(parsed.path)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/revive":
            self._json({"error": "not found"}, 404)
            return
        if self.headers.get("X-Prediction-Control-Center") != "local-ui-v1":
            self._json({"error": "missing local UI header"}, 403)
            return
        length = int(self.headers.get("Content-Length") or "0")
        if length < 1 or length > 65536:
            self._json({"error": "invalid body size"}, 400)
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            self._json({"error": "invalid json"}, 400)
            return
        candidate_id = payload.get("candidate_id") if isinstance(payload, dict) else None
        note = payload.get("note", "") if isinstance(payload, dict) else ""
        if not isinstance(candidate_id, str) or not candidate_id:
            self._json({"error": "candidate_id required"}, 400)
            return
        try:
            result = self.model.request_revive(candidate_id, note if isinstance(note, str) else "")
        except KeyError:
            self._json({"error": "candidate not found"}, 404)
            return
        except FileExistsError:
            self._json({"error": "request collision"}, 409)
            return
        self._json(result, 201)


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, handler, model, static_root):
        super().__init__(address, handler)
        self.model = model
        self.static_root = static_root.resolve()


def main():
    parser = argparse.ArgumentParser(description="Local Prediction Control Center")
    parser.add_argument("--repo", default=str(Path.home() / "prediction_research_prod"))
    parser.add_argument("--state-root", default=str(Path.home() / ".local/state/prediction-project-executor/control-center"))
    parser.add_argument("--static-root", default=str(Path(__file__).resolve().parent / "static"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8770)
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "::1", "localhost"}:
        raise SystemExit("Control Center must bind to loopback")
    model = ControlCenterModel(Path(args.repo), Path(args.state_root))
    server = Server((args.host, args.port), Handler, model, Path(args.static_root))
    print(f"PREDICTION_CONTROL_CENTER_READY http://{args.host}:{args.port} repo={model.repo}", flush=True)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
