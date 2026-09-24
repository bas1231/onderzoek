from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

import fcntl

DEFAULT_TTL_SECONDS = 900
INTEGRATION_TTL_SECONDS = 180


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)


def _git_text(root: Path, *args: str) -> str:
    result = _run_git(root, *args)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _safe_id(value: str) -> str:
    value = value.strip()
    cleaned = "".join(ch if ch.isalnum() or ch in "-_." else "-" for ch in value).strip(".-")
    if not cleaned:
        raise ValueError("empty/unsafe session id")
    return cleaned[:120]


def _norm_path(value: str) -> str:
    raw = value.strip().replace("\\", "/")
    while raw.startswith("./"):
        raw = raw[2:]
    for suffix in ("/**", "/*"):
        if raw.endswith(suffix):
            raw = raw[: -len(suffix)]
    raw = raw.rstrip("/") or "."
    path = PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe repository path: {value}")
    return path.as_posix()


def paths_overlap(left: str, right: str) -> bool:
    a = _norm_path(left)
    b = _norm_path(right)
    if a == "." or b == ".":
        return True
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def path_sets_overlap(left: list[str], right: list[str]) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    for a in left:
        for b in right:
            if paths_overlap(a, b):
                hits.append((_norm_path(a), _norm_path(b)))
    return hits


class Coordinator:
    def __init__(self, root: Path, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.root = root.resolve()
        self.runtime = self.root / ".runtime" / "build_coordination"
        self.sessions = self.runtime / "sessions"
        self.registry_lock_path = self.runtime / "registry.lock"
        self.integration_owner_path = self.runtime / "integration_owner.json"
        self.ttl_seconds = ttl_seconds
        self.sessions.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _lock(self):
        self.runtime.mkdir(parents=True, exist_ok=True)
        with self.registry_lock_path.open("a+") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _session_file(self, session_id: str) -> Path:
        return self.sessions / f"{_safe_id(session_id)}.json"

    @staticmethod
    def _read(path: Path) -> dict[str, Any] | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return None
        return data if isinstance(data, dict) else None

    @staticmethod
    def _write(path: Path, payload: dict[str, Any]) -> None:
        tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, path)

    @staticmethod
    def _active(lease: dict[str, Any], now: float) -> bool:
        expiry = lease.get("expires_at_epoch")
        return isinstance(expiry, (int, float)) and expiry >= now

    def active_sessions(self) -> list[dict[str, Any]]:
        now = time.time()
        result: list[dict[str, Any]] = []
        for path in sorted(self.sessions.glob("*.json")):
            lease = self._read(path)
            if lease and self._active(lease, now):
                result.append(lease)
        return result

    def start(self, session_id: str, task_id: str, paths: list[str], *, mutating: bool, ttl: int) -> dict[str, Any]:
        sid = _safe_id(session_id)
        normalized = sorted({_norm_path(path) for path in paths})
        if mutating and not normalized:
            raise ValueError("mutating session requires at least one planned path")
        if ttl < 30:
            raise ValueError("ttl must be >= 30 seconds")
        branch = _git_text(self.root, "branch", "--show-current")
        source = _git_text(self.root, "rev-parse", "HEAD")
        worktree = _git_text(self.root, "rev-parse", "--show-toplevel")
        now = time.time()
        with self._lock():
            conflicts: list[dict[str, Any]] = []
            for other in self.active_sessions():
                if other.get("session_id") == sid or not mutating or not other.get("mutating"):
                    continue
                same_worktree = str(Path(str(other.get("worktree", ""))).resolve()) == str(Path(worktree).resolve())
                overlaps = path_sets_overlap(normalized, list(other.get("planned_paths") or []))
                if same_worktree or overlaps:
                    conflicts.append({
                        "session_id": other.get("session_id"),
                        "task_id": other.get("task_id"),
                        "same_worktree": same_worktree,
                        "path_overlaps": overlaps,
                    })
            if conflicts:
                return {"ok": False, "status": "BLOCKED_PARALLEL_CONFLICT", "conflicts": conflicts}
            lease = {
                "schema": "PARALLEL_BUILD_SESSION_V1",
                "session_id": sid,
                "task_id": task_id,
                "mutating": mutating,
                "planned_paths": normalized,
                "branch": branch,
                "source_commit": source,
                "last_validated_main": None,
                "worktree": worktree,
                "host": socket.gethostname(),
                "status": "ACTIVE",
                "started_at": now_iso(),
                "heartbeat_at": now_iso(),
                "expires_at_epoch": now + ttl,
            }
            self._write(self._session_file(sid), lease)
            return {"ok": True, "status": "ACTIVE", "lease": lease}

    def heartbeat(self, session_id: str, ttl: int) -> dict[str, Any]:
        sid = _safe_id(session_id)
        with self._lock():
            lease = self._read(self._session_file(sid))
            if not lease:
                return {"ok": False, "status": "UNKNOWN_SESSION"}
            lease["heartbeat_at"] = now_iso()
            lease["expires_at_epoch"] = time.time() + ttl
            self._write(self._session_file(sid), lease)
            return {"ok": True, "status": lease.get("status", "ACTIVE")}

    def finish(self, session_id: str) -> dict[str, Any]:
        sid = _safe_id(session_id)
        with self._lock():
            owner = self._read(self.integration_owner_path)
            if owner and owner.get("session_id") == sid:
                self.integration_owner_path.unlink(missing_ok=True)
            self._session_file(sid).unlink(missing_ok=True)
            return {"ok": True, "status": "RELEASED"}

    def acquire_integration(self, session_id: str) -> dict[str, Any]:
        sid = _safe_id(session_id)
        now = time.time()
        with self._lock():
            lease = self._read(self._session_file(sid))
            if not lease or not self._active(lease, now):
                return {"ok": False, "status": "SESSION_NOT_ACTIVE"}
            owner = self._read(self.integration_owner_path)
            if owner and float(owner.get("expires_at_epoch", 0)) >= now and owner.get("session_id") != sid:
                return {"ok": False, "status": "BLOCKED_INTEGRATION_LOCK", "owner": owner}
            lock = {
                "schema": "PARALLEL_BUILD_INTEGRATION_LOCK_V1",
                "session_id": sid,
                "task_id": lease.get("task_id"),
                "acquired_at": now_iso(),
                "expires_at_epoch": now + INTEGRATION_TTL_SECONDS,
            }
            self._write(self.integration_owner_path, lock)
            lease["status"] = "INTEGRATING"
            lease["heartbeat_at"] = now_iso()
            lease["expires_at_epoch"] = max(float(lease.get("expires_at_epoch", 0)), now + INTEGRATION_TTL_SECONDS)
            self._write(self._session_file(sid), lease)
            return {"ok": True, "status": "INTEGRATION_LOCK_ACQUIRED", "lock": lock}

    def release_integration(self, session_id: str) -> dict[str, Any]:
        sid = _safe_id(session_id)
        with self._lock():
            owner = self._read(self.integration_owner_path)
            if not owner:
                return {"ok": True, "status": "NO_INTEGRATION_LOCK"}
            if owner.get("session_id") != sid:
                return {"ok": False, "status": "NOT_INTEGRATION_OWNER", "owner": owner}
            self.integration_owner_path.unlink(missing_ok=True)
            lease = self._read(self._session_file(sid))
            if lease:
                lease["status"] = "ACTIVE"
                self._write(self._session_file(sid), lease)
            return {"ok": True, "status": "INTEGRATION_LOCK_RELEASED"}

    def _owned_lock_and_lease(self, sid: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None, float]:
        now = time.time()
        with self._lock():
            return self._read(self._session_file(sid)), self._read(self.integration_owner_path), now

    def premerge(self, session_id: str) -> dict[str, Any]:
        sid = _safe_id(session_id)
        lease, owner, now = self._owned_lock_and_lease(sid)
        if not lease or not self._active(lease, now):
            return {"ok": False, "status": "SESSION_NOT_ACTIVE"}
        if not owner or owner.get("session_id") != sid or float(owner.get("expires_at_epoch", 0)) < now:
            return {"ok": False, "status": "INTEGRATION_LOCK_REQUIRED"}
        fetched = _run_git(self.root, "fetch", "origin", "main")
        if fetched.returncode != 0:
            return {"ok": False, "status": "FETCH_FAILED", "stderr": fetched.stderr[-4000:]}
        origin_main = _git_text(self.root, "rev-parse", "origin/main")
        source = str(lease.get("source_commit") or "")
        if source == origin_main:
            return {"ok": True, "status": "CURRENT_MAIN", "origin_main": origin_main, "revalidation_required": False}
        diff = _run_git(self.root, "diff", "--name-only", f"{source}..{origin_main}")
        if diff.returncode != 0:
            return {"ok": False, "status": "MAIN_DIFF_FAILED", "stderr": diff.stderr[-4000:]}
        changed = [line.strip() for line in diff.stdout.splitlines() if line.strip()]
        overlaps = path_sets_overlap(list(lease.get("planned_paths") or []), changed)
        if overlaps:
            return {"ok": False, "status": "BLOCKED_OVERLAPPING_MAIN_CHANGE", "origin_main": origin_main, "changed_paths": changed, "path_overlaps": overlaps}
        return {"ok": True, "status": "STALE_MAIN_REVALIDATION_REQUIRED", "origin_main": origin_main, "changed_paths": changed, "revalidation_required": True}

    def mark_validated(self, session_id: str, main_sha: str) -> dict[str, Any]:
        sid = _safe_id(session_id)
        current = _git_text(self.root, "rev-parse", "origin/main")
        if current != main_sha:
            return {"ok": False, "status": "MAIN_MOVED_DURING_VALIDATION", "origin_main": current}
        with self._lock():
            lease = self._read(self._session_file(sid))
            if not lease:
                return {"ok": False, "status": "UNKNOWN_SESSION"}
            lease["last_validated_main"] = main_sha
            lease["heartbeat_at"] = now_iso()
            self._write(self._session_file(sid), lease)
            return {"ok": True, "status": "VALIDATED", "main_sha": main_sha}

    def publish_check(self, session_id: str) -> dict[str, Any]:
        sid = _safe_id(session_id)
        lease, owner, now = self._owned_lock_and_lease(sid)
        if not lease or not self._active(lease, now):
            return {"ok": False, "status": "SESSION_NOT_ACTIVE"}
        if not owner or owner.get("session_id") != sid or float(owner.get("expires_at_epoch", 0)) < now:
            return {"ok": False, "status": "INTEGRATION_LOCK_REQUIRED"}
        fetched = _run_git(self.root, "fetch", "origin", "main")
        if fetched.returncode != 0:
            return {"ok": False, "status": "FETCH_FAILED", "stderr": fetched.stderr[-4000:]}
        origin_main = _git_text(self.root, "rev-parse", "origin/main")
        if lease.get("last_validated_main") != origin_main:
            return {"ok": False, "status": "REVALIDATION_REQUIRED", "validated_main": lease.get("last_validated_main"), "origin_main": origin_main}
        if _run_git(self.root, "merge-base", "--is-ancestor", "origin/main", "HEAD").returncode != 0:
            return {"ok": False, "status": "BRANCH_NOT_BASED_ON_CURRENT_MAIN", "origin_main": origin_main}
        dirty = _run_git(self.root, "status", "--porcelain", "--untracked-files=no")
        if dirty.returncode != 0 or dirty.stdout.strip():
            return {"ok": False, "status": "TRACKED_WORKTREE_DIRTY", "detail": dirty.stdout[-4000:]}
        return {"ok": True, "status": "PUBLISH_ALLOWED", "origin_main": origin_main, "head": _git_text(self.root, "rev-parse", "HEAD")}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Coordinate parallel mutating build sessions")
    parser.add_argument("--root", default=".")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("start")
    p.add_argument("--session-id", required=True)
    p.add_argument("--task-id", required=True)
    p.add_argument("--path", action="append", default=[])
    p.add_argument("--read-only", action="store_true")
    p.add_argument("--ttl", type=int, default=DEFAULT_TTL_SECONDS)
    p = sub.add_parser("status")
    p.add_argument("--session-id")
    p = sub.add_parser("heartbeat")
    p.add_argument("--session-id", required=True)
    p.add_argument("--ttl", type=int, default=DEFAULT_TTL_SECONDS)
    for name in ("finish", "acquire-integration", "release-integration", "premerge", "publish-check"):
        p = sub.add_parser(name)
        p.add_argument("--session-id", required=True)
    p = sub.add_parser("mark-validated")
    p.add_argument("--session-id", required=True)
    p.add_argument("--main-sha", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    coord = Coordinator(Path(args.root))
    if args.command == "start":
        result = coord.start(args.session_id, args.task_id, args.path, mutating=not args.read_only, ttl=args.ttl)
    elif args.command == "status":
        sessions = coord.active_sessions()
        if args.session_id:
            sessions = [item for item in sessions if item.get("session_id") == args.session_id]
        result = {"ok": True, "status": "OK", "sessions": sessions}
    elif args.command == "heartbeat":
        result = coord.heartbeat(args.session_id, args.ttl)
    elif args.command == "finish":
        result = coord.finish(args.session_id)
    elif args.command == "acquire-integration":
        result = coord.acquire_integration(args.session_id)
    elif args.command == "release-integration":
        result = coord.release_integration(args.session_id)
    elif args.command == "premerge":
        result = coord.premerge(args.session_id)
    elif args.command == "mark-validated":
        result = coord.mark_validated(args.session_id, args.main_sha)
    elif args.command == "publish-check":
        result = coord.publish_check(args.session_id)
    else:
        raise AssertionError(args.command)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
