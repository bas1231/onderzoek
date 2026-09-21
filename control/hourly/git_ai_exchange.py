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
            result = receiver.receive({"run_id": run_id, "response": response})
            applied.append({
                "run_id": run_id,
                "already_applied": bool(result.get("already_applied")),
                "response_ref": result.get("response_ref"),
                "receipt_ref": result.get("receipt_ref"),
                "role_statuses": result.get("role_statuses", {}),
                "had_final_response_before": final_response.exists(),
            })
        except Exception as exc:
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
            "errors": [{
                "error_type": type(exc).__name__,
                "error": str(exc)[:1000],
            }],
            "economic_conclusion": "NO_PROVEN_EDGE",
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
        }
