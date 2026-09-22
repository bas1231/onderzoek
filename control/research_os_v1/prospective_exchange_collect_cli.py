from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from .prospective_collector import safe_cycle_filename, write_cycle_capture
from .prospective_exchange import build_exchange_shadow_bundle


_SAFE_CANDIDATE = re.compile(r"^[A-Za-z0-9_.-]+$")


def _load_object(path: Path) -> dict[str, Any]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid_json:{path}:{type(exc).__name__}") from exc
    if not isinstance(obj, dict):
        raise ValueError(f"json_object_required:{path}")
    return obj


def _request_candidate_ids(request: dict[str, Any]) -> list[str]:
    ids: set[str] = set()
    work_items = request.get("work_items")
    if not isinstance(work_items, list):
        raise ValueError("request_work_items_required")
    for index, item in enumerate(work_items):
        if not isinstance(item, dict):
            raise ValueError(f"work_item_must_be_object:{index}")
        packet = item.get("packet")
        if not isinstance(packet, dict):
            raise ValueError(f"work_item_packet_required:{index}")
        for key in ("candidate_ids", "survivors", "reproduction_candidates"):
            values = packet.get(key, [])
            if values is None:
                continue
            if not isinstance(values, list):
                raise ValueError(f"packet_{key}_must_be_list:{index}")
            for value in values:
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"packet_{key}_invalid:{index}")
                cid = value.strip()
                if not _SAFE_CANDIDATE.fullmatch(cid):
                    raise ValueError(f"unsafe_candidate_id:{cid}")
                ids.add(cid)
    return sorted(ids)


def _git_show_candidate(repo_root: Path, source_commit: str, candidate_id: str) -> dict[str, Any]:
    spec = f"{source_commit}:knowledge/candidates/{candidate_id}.json"
    proc = subprocess.run(
        ["git", "show", spec],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        raise ValueError(f"candidate_at_source_commit_unavailable:{candidate_id}")
    try:
        obj = json.loads(proc.stdout)
    except Exception as exc:
        raise ValueError(f"candidate_json_invalid:{candidate_id}:{type(exc).__name__}") from exc
    if not isinstance(obj, dict) or obj.get("candidate_id") != candidate_id:
        raise ValueError(f"candidate_identity_mismatch:{candidate_id}")
    return obj


def _write_immutable(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") == encoded:
            return {"status": "IDEMPOTENT", "path": str(path)}
        raise ValueError(f"immutable_artifact_conflict:{path}")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(encoded, encoding="utf-8")
    tmp.replace(path)
    return {"status": "CREATED", "path": str(path)}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Collect one prospectively eligible ai/runtime-exchange request/response "
            "pair into immutable Research OS shadow artifacts."
        )
    )
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--response", required=True, type=Path)
    parser.add_argument("--collection-dir", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()

    request = _load_object(args.request)
    response = _load_object(args.response)
    source_commit = request.get("source_commit")
    if not isinstance(source_commit, str) or not source_commit.strip():
        raise ValueError("source_commit_required")
    candidate_ids = _request_candidate_ids(request)
    candidate_records = [
        _git_show_candidate(args.repo_root, source_commit.strip(), cid)
        for cid in candidate_ids
    ]

    bundle = build_exchange_shadow_bundle(request, response, candidate_records)
    cycle_write = write_cycle_capture(args.collection_dir, bundle["cycle_capture"])
    filename = safe_cycle_filename(bundle["run_id"])

    baseline_payload = {
        "schema_version": 1,
        "side": "BASELINE",
        "run_id": bundle["run_id"],
        "source_commit": bundle["source_commit"],
        "request_sha256": bundle["request_sha256"],
        "records": bundle["baseline_records"],
        "economic_conclusion": "NO_PROVEN_EDGE",
    }
    challenger_payload = {
        "schema_version": 1,
        "side": "CHALLENGER",
        "run_id": bundle["run_id"],
        "source_commit": bundle["source_commit"],
        "request_sha256": bundle["request_sha256"],
        "selected_roles": bundle["challenger_selected_roles"],
        "records": bundle["challenger_records"],
        "economic_conclusion": "NO_PROVEN_EDGE",
    }

    raw_dir = args.collection_dir / "raw_telemetry"
    baseline_write = _write_immutable(raw_dir / "baseline" / filename, baseline_payload)
    challenger_write = _write_immutable(raw_dir / "challenger" / filename, challenger_payload)
    bundle_write = _write_immutable(
        args.collection_dir / "exchange_bundles" / filename,
        bundle,
    )

    print(json.dumps({
        "status": "PASS",
        "run_id": bundle["run_id"],
        "case_count": bundle["cycle_capture"]["case_count"],
        "challenger_selected_roles": bundle["challenger_selected_roles"],
        "cycle_write": cycle_write,
        "baseline_write": baseline_write,
        "challenger_write": challenger_write,
        "bundle_write": bundle_write,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "runtime_mutation": False,
        "economic_conclusion": "NO_PROVEN_EDGE",
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
