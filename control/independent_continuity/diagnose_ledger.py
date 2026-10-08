"""Read-only classifier of the exact FETCH_HEAD build-log event tree.

This is a diagnostic of the isolated continuity observer, not an alternative
bridge, data repair or authorization to discard malformed ledger events.
"""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import PurePosixPath, Path
import subprocess

PREFIX = "control/build_log/events/"
MAX_FILES = 12000
MAX_SIZE = 1024 * 1024
VALID_EVENTS = {"PLAN", "ATTEMPT", "RESULT", "DECISION", "HANDOFF", "CLOSE", "NOTE"}
VALID_STATES = {"OPEN", "IN_PROGRESS", "BLOCKED", "DONE"}


def verify_bytes(filename: str, raw: bytes) -> str | None:
    if not filename.endswith(".json") or "/" in filename or len(filename) > 250:
        return "unexpected_filename"
    if len(raw) > MAX_SIZE:
        return "oversized"
    try:
        obj = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError):
        return "invalid_json"
    if not isinstance(obj, dict):
        return "not_object"
    if obj.get("schema") != "PREDICTION_BUILD_LOG_EVENT_V1":
        return "invalid_schema"
    if obj.get("event_id") != filename[:-5]:
        return "event_id_filename_mismatch"
    if not isinstance(obj.get("work_item_id"), str) or not obj["work_item_id"]:
        return "missing_work_item_id"
    stamp = obj.get("created_at_utc")
    if not isinstance(stamp, str):
        return "missing_created_at_utc"
    try:
        at = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return "invalid_created_at_utc"
    if at.tzinfo is None:
        return "naive_created_at_utc"
    if obj.get("event_type") not in VALID_EVENTS:
        return "invalid_event_type"
    if obj.get("work_item_status") not in VALID_STATES:
        return "invalid_work_item_status"
    return None


def git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, timeout=25, check=False,
    )
    if result.returncode:
        raise RuntimeError("local_git_read_failed")
    return result.stdout


def diagnose(repo: Path) -> tuple[int, str]:
    revision = git(repo, "rev-parse", "--verify", "FETCH_HEAD").decode("ascii").strip()
    if len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
        raise RuntimeError("bad_fetched_revision")
    listing = git(repo, "ls-tree", "-r", "--name-only", revision, "--", PREFIX)
    paths = listing.decode("utf-8", errors="strict").splitlines()
    if not paths or len(paths) > MAX_FILES:
        raise RuntimeError("ledger_tree_missing_or_too_large")
    count = 0
    faults: list[str] = []
    for rel in paths:
        if not rel.startswith(PREFIX):
            raise RuntimeError("unexpected_tree_path")
        leaf = rel[len(PREFIX):]
        if PurePosixPath(leaf).name != leaf or not leaf.endswith(".json"):
            faults.append("invalid_event_path")
            break
        raw = git(repo, "show", f"{revision}:{rel}")
        issue = verify_bytes(leaf, raw)
        count += 1
        if issue:
            faults.append(f"{leaf}:{issue}")
            if len(faults) == 2:
                break
    if faults:
        return 2, "LEDGER_INVALID=" + " | ".join(faults)[:245]
    return 0, f"LEDGER_VALID=checked_{count}_events"


def main() -> int:
    repo = Path.home() / ".local/share/prediction-project-executor/repo"
    try:
        code, message = diagnose(repo)
    except (OSError, RuntimeError, UnicodeError, subprocess.SubprocessError) as exc:
        code, message = 2, "LEDGER_DIAG_BLOCKED=" + type(exc).__name__
    print(message, flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
