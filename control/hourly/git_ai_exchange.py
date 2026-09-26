from __future__ import annotations

from pathlib import Path
from typing import Any
import importlib.util
import json
import os
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
EXCHANGE_BRANCH = "ai/runtime-exchange"
REMOTE_REF = f"refs/remotes/origin/{EXCHANGE_BRANCH}"
REQUEST_PREFIX = "ai_exchange/requests"
RESPONSE_PREFIX = "ai_exchange/responses"

# E004: immutable, exact historical protocol failures that pre-date the current
# six-role response contract.  A response is quarantined only when both its
# exchange path and Git blob SHA match this registry and the observed failure
# still has the expected validation signature.  New or modified failures stay
# fail-closed in the normal errors list.
HISTORICAL_RESPONSE_QUARANTINE: dict[str, dict[str, str]] = {
    "ai_exchange/responses/hourly-20260922T150000+0200.json": {
        "blob_sha": "95f6fa87c56604b71520d0cdc321f300c431f494",
        "error_type": "ValidationError",
        "error_prefix": "invalid agent_id: recon_scout",
        "reason": "PRE_E001_LEGACY_ROLE_CONTRACT",
    },
    "ai_exchange/responses/hourly-20260923T090000+0200.json": {
        "blob_sha": "5e8c8f3e6899f1bafdfe6f9275fe7d144cc0e93b",
        "error_type": "ValidationError",
        "error_prefix": "invalid validation status:",
        "reason": "PRE_E003_VALIDATION_RESULT_CONTRACT",
    },
    "ai_exchange/responses/hourly-20260923T120000+0200.json": {
        "blob_sha": "7aba670f82b757d494c9d04d5a53b39a72f3cb91",
        "error_type": "GitExchangeError",
        "error_prefix": "invalid response run_id",
        "reason": "PRE_E005_LEGACY_RESPONSE_ENVELOPE_RUN_ID",
    },
    "ai_exchange/responses/hourly-20260923T130000+0200.json": {
        "blob_sha": "24aa92c50fb0e67b19d8c39f7010dd3b8619e6b9",
        "error_type": "GitExchangeError",
        "error_prefix": "invalid response run_id",
        "reason": "PRE_E005_LEGACY_RESPONSE_ENVELOPE_RUN_ID",
    },
    "ai_exchange/responses/hourly-20260923T140000+0200.json": {
        "blob_sha": "5d1d4c12ead4ff34a1cd22d694580bee0573b9e4",
        "error_type": "GitExchangeError",
        "error_prefix": "invalid response run_id",
        "reason": "PRE_E005_LEGACY_RESPONSE_ENVELOPE_RUN_ID",
    },
}


class GitExchangeError(RuntimeError):
    pass


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {name} from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.modules.pop(spec.name, None)
        raise
    return mod


def _git(
    args: list[str],
    *,
    input_text: str | None = None,
    env: dict[str, str] | None = None,
    timeout: int = 45,
) -> subprocess.CompletedProcess[str]:
    if os.environ.get("PREDICTION_EXECUTION_MODE", "production") != "production":
        raise RuntimeError("REMOTE_GIT_CAPABILITY_FORBIDDEN")
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        input=input_text,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
        env=merged,
    )


def _require_ok(proc: subprocess.CompletedProcess[str], action: str) -> str:
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()[-2000:]
        raise GitExchangeError(f"{action} failed: {detail}")
    return proc.stdout.strip()


def fetch_exchange() -> str:
    proc = _git([
        "fetch",
        "origin",
        f"+refs/heads/{EXCHANGE_BRANCH}:{REMOTE_REF}",
    ])
    _require_ok(proc, "fetch exchange branch")
    head = _git(["rev-parse", "--verify", REMOTE_REF])
    return _require_ok(head, "resolve exchange head")


def _show(ref: str, path: str) -> str | None:
    proc = _git(["show", f"{ref}:{path}"])
    if proc.returncode != 0:
        return None
    return proc.stdout


def _blob_sha(ref: str, path: str) -> str | None:
    proc = _git(["rev-parse", "--verify", f"{ref}:{path}"])
    if proc.returncode != 0:
        return None
    value = proc.stdout.strip()
    return value if len(value) == 40 else None


def _historical_quarantine_record(
    ref: str,
    remote_path: str,
    exc: Exception,
) -> dict[str, Any] | None:
    rule = HISTORICAL_RESPONSE_QUARANTINE.get(remote_path)
    if rule is None:
        return None

    blob_sha = _blob_sha(ref, remote_path)
    if blob_sha != rule["blob_sha"]:
        return None

    error_type = type(exc).__name__
    error = str(exc)[:1000]
    if error_type != rule["error_type"]:
        return None
    if not error.startswith(rule["error_prefix"]):
        return None

    return {
        "path": remote_path,
        "blob_sha": blob_sha,
        "reason": rule["reason"],
        "error_type": error_type,
        "error": error,
    }


def _semantic_json_equal(left: str, right: dict[str, Any]) -> bool:
    try:
        return json.loads(left) == right
    except Exception:
        return False


def _commit_file_on_parent(
    parent: str,
    remote_path: str,
    value: dict[str, Any],
    message: str,
) -> str:
    content = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    blob = _require_ok(
        _git(["hash-object", "-w", "--stdin"], input_text=content),
        "write exchange blob",
    )

    fd, index_path = tempfile.mkstemp(prefix="pva-ai-exchange-index-")
    os.close(fd)
    try:
        os.unlink(index_path)
    except FileNotFoundError:
        pass

    env = {"GIT_INDEX_FILE": index_path}
    try:
        _require_ok(_git(["read-tree", parent], env=env), "read exchange tree")
        cacheinfo = f"100644,{blob},{remote_path}"
        _require_ok(
            _git(["update-index", "--add", "--cacheinfo", cacheinfo], env=env),
            "stage exchange file",
        )
        tree = _require_ok(_git(["write-tree"], env=env), "write exchange tree")
    finally:
        try:
            os.unlink(index_path)
        except FileNotFoundError:
            pass

    commit = _require_ok(
        _git(["commit-tree", tree, "-p", parent, "-m", message]),
        "create exchange commit",
    )
    return commit


def publish_request(request: dict[str, Any], *, retries: int = 3) -> dict[str, Any]:
    contract = load_module(
        "prediction_ai_exchange_contract_publish",
        ROOT / "control/hourly/ai_work_exchange.py",
    )
    request = contract.validate_request(request)
    run_id = str(request["run_id"])
    work_items = request.get("work_items", [])
    if not work_items:
        return {
            "ok": True,
            "status": "NO_WORK",
            "run_id": run_id,
            "published": False,
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
        }

    remote_path = f"{REQUEST_PREFIX}/{run_id}.json"
    for attempt in range(1, retries + 1):
        parent = fetch_exchange()
        existing = _show(parent, remote_path)
        if existing is not None:
            if _semantic_json_equal(existing, request):
                return {
                    "ok": True,
                    "status": "ALREADY_PUBLISHED",
                    "run_id": run_id,
                    "published": True,
                    "exchange_commit": parent,
                    "request_path": remote_path,
                    "live_trading": False,
                    "paid_actions": False,
                    "wallet_actions": False,
                }
            raise GitExchangeError(f"conflicting request already exists: {run_id}")

        commit = _commit_file_on_parent(
            parent,
            remote_path,
            request,
            f"ai-exchange: request {run_id}",
        )
        push = _git([
            "push",
            "origin",
            f"{commit}:refs/heads/{EXCHANGE_BRANCH}",
        ])
        if push.returncode == 0:
            return {
                "ok": True,
                "status": "PUBLISHED",
                "run_id": run_id,
                "published": True,
                "exchange_commit": commit,
                "request_path": remote_path,
                "attempt": attempt,
                "live_trading": False,
                "paid_actions": False,
                "wallet_actions": False,
            }

    raise GitExchangeError(f"exchange push race unresolved after {retries} attempts")


def safe_publish_request(request: dict[str, Any]) -> dict[str, Any]:
    try:
        return publish_request(request)
    except Exception as exc:
        return {
            "ok": False,
            "status": "TRANSPORT_UNAVAILABLE",
            "run_id": request.get("run_id"),
            "published": False,
            "error_type": type(exc).__name__,
            "error": str(exc)[:1000],
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
        }


def _response_paths(ref: str) -> list[str]:
    proc = _git([
        "ls-tree",
        "-r",
        "--name-only",
        ref,
        RESPONSE_PREFIX,
    ])
    if proc.returncode != 0:
        return []
    return sorted(
        line.strip()
        for line in proc.stdout.splitlines()
        if line.strip().startswith(RESPONSE_PREFIX + "/")
        and line.strip().endswith(".json")
    )


def _validate_envelope(envelope: Any) -> tuple[str, dict[str, Any], str]:
    if not isinstance(envelope, dict):
        raise GitExchangeError("response envelope must be object")
    if envelope.get("schema") != "PVA_AI_EXCHANGE_RESPONSE_V1":
        raise GitExchangeError("unexpected response envelope schema")
    run_id = envelope.get("run_id")
    if not isinstance(run_id, str) or not run_id.startswith("hourly-"):
        raise GitExchangeError("invalid response run_id")
    request_sha = envelope.get("request_sha256")
    if not isinstance(request_sha, str) or len(request_sha) != 64:
        raise GitExchangeError("response request_sha256 missing")
    response = envelope.get("response")
    if not isinstance(response, dict):
        raise GitExchangeError("response payload missing")
    if response.get("run_id") != run_id:
        raise GitExchangeError("response envelope run mismatch")
    return run_id, response, request_sha


def ingest_remote_responses(*, limit: int = 32) -> dict[str, Any]:
    ref = fetch_exchange()
    contract = load_module(
        "prediction_ai_exchange_contract_ingest",
        ROOT / "control/hourly/ai_work_exchange.py",
    )
    receiver = load_module(
        "prediction_ai_exchange_receiver_ingest",
        ROOT / "control/hourly/ai_response_receiver.py",
    )

    applied: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for remote_path in _response_paths(ref)[-limit:]:
        raw = _show(ref, remote_path)
        if raw is None:
            continue
        try:
            envelope = json.loads(raw)
            run_id, response, request_sha = _validate_envelope(envelope)
            local_request_path = (
                ROOT / "knowledge/ai_exchange/requests" / f"{run_id}.json"
            )
            if not local_request_path.exists():
                skipped.append({"run_id": run_id, "reason": "NO_LOCAL_REQUEST"})
                continue
            local_request = json.loads(local_request_path.read_text(encoding="utf-8"))
            local_request = contract.validate_request(local_request)
            if local_request.get("request_sha256") != request_sha:
                raise GitExchangeError("response does not match local request_sha256")

            final_response = ROOT / "knowledge/runs" / f"{run_id}-ai-response.json"
            receipt = ROOT / "knowledge/runs" / f"{run_id}-ai-response-receipt.json"
            orchestration = (
                ROOT
                / "knowledge/runs/agent_packets"
                / run_id
                / "_orchestration.json"
            )
            response_existed_before = final_response.exists()
            complete_before = (
                response_existed_before
                and receipt.exists()
                and orchestration.exists()
            )
            if complete_before:
                skipped.append({"run_id": run_id, "reason": "ALREADY_APPLIED"})
                continue

            result = receiver.receive({"run_id": run_id, "response": response})
            applied.append({
                "run_id": run_id,
                "already_applied": bool(result.get("already_applied")),
                "response_ref": result.get("response_ref"),
                "receipt_ref": result.get("receipt_ref"),
                "role_statuses": result.get("role_statuses", {}),
                "recovery_retry": response_existed_before,
            })
        except Exception as exc:
            quarantine = _historical_quarantine_record(ref, remote_path, exc)
            if quarantine is not None:
                quarantined.append(quarantine)
                continue
            errors.append({
                "path": remote_path,
                "error_type": type(exc).__name__,
                "error": str(exc)[:1000],
            })

    return {
        "ok": not errors,
        "status": "APPLIED" if applied else "NO_APPLICABLE_RESPONSES",
        "exchange_commit": ref,
        "applied": applied,
        "skipped": skipped,
        "quarantined": quarantined,
        "errors": errors,
        "economic_conclusion": "NO_PROVEN_EDGE",
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
    }


def safe_ingest_remote_responses(*, limit: int = 32) -> dict[str, Any]:
    try:
        return ingest_remote_responses(limit=limit)
    except Exception as exc:
        return {
            "ok": False,
            "status": "TRANSPORT_UNAVAILABLE",
            "applied": [],
            "skipped": [],
            "quarantined": [],
            "errors": [{
                "error_type": type(exc).__name__,
                "error": str(exc)[:1000],
            }],
            "economic_conclusion": "NO_PROVEN_EDGE",
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
        }
