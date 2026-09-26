from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
STATUS_PATH = (
    Path.home()
    / ".local/state/prediction-research/prod-runtime-sync-latest.json"
)


class RuntimeSyncError(RuntimeError):
    pass


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(spec.name, None)
        raise
    return module


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=120,
    )


def require_ok(proc: subprocess.CompletedProcess[str], action: str) -> str:
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()[-2000:]
        raise RuntimeSyncError(f"{action} failed: {detail}")
    return proc.stdout.strip()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_status(status: str, **extra: Any) -> dict[str, Any]:
    payload = {
        "schema": "PVA_PROD_RUNTIME_SYNC_V1",
        "timestamp_utc": now_iso(),
        "status": status,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "openai_api": False,
        **extra,
    }
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def tracked_changes() -> list[str]:
    proc = git("diff", "--name-only", "HEAD", "--")
    out = require_ok(proc, "list tracked changes")
    return sorted({line.strip() for line in out.splitlines() if line.strip()})


def staged_changes() -> list[str]:
    proc = git("diff", "--cached", "--name-only", "--")
    out = require_ok(proc, "list staged changes")
    return sorted({line.strip() for line in out.splitlines() if line.strip()})


def untracked_paths() -> list[str]:
    proc = git("ls-files", "--others", "--exclude-standard")
    out = require_ok(proc, "list untracked files")
    return sorted({line.strip() for line in out.splitlines() if line.strip()})


def untracked_count() -> int:
    return len(untracked_paths())


def classify_tracked_paths(
    paths: list[str],
    checkpoint: Any,
) -> tuple[list[str], list[str]]:
    safe: list[str] = []
    unexpected: list[str] = []
    for path in sorted(set(paths)):
        if checkpoint.denied(path) or not checkpoint.matches_allow(path):
            unexpected.append(path)
        else:
            safe.append(path)
    return safe, unexpected


def checkpointable_untracked_paths(
    paths: list[str],
    checkpoint: Any,
) -> list[str]:
    """Return only untracked paths the durable checkpoint is allowed to publish.

    Other untracked runtime files remain deliberately untouched. They are not
    treated as tracked-code drift, but they must not prevent new durable
    receipts/reports from triggering the checkpoint publisher.
    """
    return sorted({
        path
        for path in paths
        if not checkpoint.denied(path) and checkpoint.matches_allow(path)
    })


def changed_between(base: str, head: str) -> list[str]:
    proc = git("diff", "--name-only", f"{base}..{head}", "--")
    out = require_ok(proc, "list remote changes")
    return sorted({line.strip() for line in out.splitlines() if line.strip()})


def is_ancestor(base: str, head: str) -> bool:
    proc = git("merge-base", "--is-ancestor", base, head)
    if proc.returncode == 0:
        return True
    if proc.returncode == 1:
        return False
    require_ok(proc, "check ancestry")
    return False


def run_checkpoint() -> dict[str, Any]:
    checkpoint_script = ROOT / "control/hourly/git_checkpoint.py"
    proc = subprocess.run(
        [sys.executable, str(checkpoint_script)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=180,
    )
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip()[-4000:],
        "stderr": proc.stderr.strip()[-4000:],
    }


def sync() -> dict[str, Any]:
    mode = os.environ.get("PREDICTION_EXECUTION_MODE", "production")
    if mode not in ("production", "qualification_local"):
        raise RuntimeSyncError("UNKNOWN_EXECUTION_MODE")
    if mode == "qualification_local":
        local = load_module("prediction_local_runtime", ROOT / "control/hourly/local_runtime.py")
        result = local.preflight(ROOT)
        return write_status("READY", **{k:v for k,v in result.items() if k != "status"})
    checkpoint = load_module(
        "prediction_runtime_sync_checkpoint",
        ROOT / "control/hourly/git_checkpoint.py",
    )

    branch = require_ok(git("branch", "--show-current"), "read branch")
    if branch != "main":
        raise RuntimeSyncError(f"unexpected branch: {branch!r}; production requires main")

    staged = staged_changes()
    if staged:
        raise RuntimeSyncError(
            "git index is not empty: " + ", ".join(staged[:20])
        )

    fetch = git("fetch", "origin", "main")
    require_ok(fetch, "fetch origin/main")

    local_before = require_ok(git("rev-parse", "HEAD"), "resolve local HEAD")
    remote_before = require_ok(
        git("rev-parse", "origin/main"),
        "resolve origin/main",
    )

    tracked = tracked_changes()
    safe, unexpected = classify_tracked_paths(tracked, checkpoint)
    untracked_before = untracked_paths()
    safe_untracked = checkpointable_untracked_paths(
        untracked_before,
        checkpoint,
    )
    untracked = len(untracked_before)

    if unexpected:
        raise RuntimeSyncError(
            "unexpected tracked changes: " + ", ".join(unexpected[:20])
        )

    ff_performed = False
    remote_changes: list[str] = []

    if local_before != remote_before:
        if not is_ancestor(local_before, remote_before):
            raise RuntimeSyncError(
                "local main is ahead or diverged from origin/main"
            )

        remote_changes = changed_between(local_before, remote_before)
        local_durable = set(safe).union(safe_untracked)
        overlap = sorted(local_durable.intersection(remote_changes))
        if overlap:
            raise RuntimeSyncError(
                "remote update overlaps local durable state: "
                + ", ".join(overlap[:20])
            )

        require_ok(
            git("merge", "--ff-only", "origin/main"),
            "fast-forward production runtime",
        )
        ff_performed = True

    checkpoint_result: dict[str, Any] | None = None
    safe_after_ff, unexpected_after_ff = classify_tracked_paths(
        tracked_changes(),
        checkpoint,
    )
    if unexpected_after_ff:
        raise RuntimeSyncError(
            "unexpected tracked changes after fast-forward: "
            + ", ".join(unexpected_after_ff[:20])
        )

    safe_untracked_after_ff = checkpointable_untracked_paths(
        untracked_paths(),
        checkpoint,
    )

    if safe_after_ff or safe_untracked_after_ff:
        checkpoint_result = run_checkpoint()
        if not checkpoint_result["ok"]:
            raise RuntimeSyncError(
                "durable checkpoint failed: "
                + (checkpoint_result.get("stderr") or checkpoint_result.get("stdout") or "unknown")[-1500:]
            )

    # Re-fetch after any checkpoint/push so final equality is checked against
    # the actual current remote state. No merge/rebase/reset/stash/clean is
    # ever used for recovery here; a race simply fails closed.
    require_ok(git("fetch", "origin", "main"), "final fetch origin/main")
    local_after = require_ok(git("rev-parse", "HEAD"), "resolve final local HEAD")
    remote_after = require_ok(
        git("rev-parse", "origin/main"),
        "resolve final origin/main",
    )

    if local_after != remote_after:
        raise RuntimeSyncError(
            "origin/main changed during runtime sync; retry on next cycle"
        )

    remaining = tracked_changes()
    safe_remaining, unexpected_remaining = classify_tracked_paths(
        remaining,
        checkpoint,
    )
    safe_untracked_remaining = checkpointable_untracked_paths(
        untracked_paths(),
        checkpoint,
    )
    durable_remaining = (
        safe_remaining
        + unexpected_remaining
        + safe_untracked_remaining
    )
    if durable_remaining:
        raise RuntimeSyncError(
            "durable changes remain after sync/checkpoint: "
            + ", ".join(durable_remaining[:20])
        )

    return write_status(
        "READY",
        branch=branch,
        local_before=local_before,
        remote_before=remote_before,
        head=local_after,
        fast_forward=ff_performed,
        checkpoint=checkpoint_result,
        durable_state_seen=sorted(set(safe).union(safe_untracked)),
        durable_untracked_seen=safe_untracked,
        remote_change_count=len(remote_changes),
        untracked_file_count=untracked,
    )


def safe_sync() -> dict[str, Any]:
    try:
        return sync()
    except Exception as exc:
        return write_status(
            "BLOCKED",
            error_type=type(exc).__name__,
            error=str(exc)[:3000],
        )


def main() -> int:
    result = safe_sync()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
