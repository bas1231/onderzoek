from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import json

MARKER = "## Candidate outcomes"


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return value if isinstance(value, dict) else None


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _review_binding(overlay: dict[str, Any], phase: str) -> str | None:
    if phase not in {"PREBUILD", "PREMEASUREMENT"}:
        return None
    if not isinstance(overlay, dict) or not overlay.get("candidate_id"):
        return None
    payload = {
        "phase": phase,
        "candidate_id": overlay.get("candidate_id"),
        "source_hashes": overlay.get("source_hashes"),
        "originating_task_id": overlay.get("originating_task_id"),
        "completion_hash": overlay.get("completion_hash"),
        "validation_hash": overlay.get("validation_hash"),
        "finding": overlay.get("finding"),
        "next_action": overlay.get("next_action"),
        "candidate_snapshot": overlay.get("candidate_snapshot"),
        "referenced_evidence_hash": _canonical_sha(overlay.get("referenced_evidence", {})),
    }
    return _canonical_sha(payload)


def _current_review(overlay: dict[str, Any] | None, phase: str) -> dict[str, Any]:
    if not isinstance(overlay, dict):
        return {}
    reviews = overlay.get("astra_reviews")
    review = reviews.get(phase) if isinstance(reviews, dict) else None
    if not isinstance(review, dict):
        return {}
    binding = _review_binding(overlay, phase)
    if not binding or review.get("binding_sha256") != binding:
        return {}
    return review


def overlay_history(runtime_root: Path, candidate_id: str) -> list[dict[str, Any]]:
    root = Path(runtime_root) / "candidate_states"
    if not root.exists():
        return []
    matches = []
    for path in root.glob("*.json"):
        if path.is_symlink():
            continue
        obj = _load_json(path)
        if obj and obj.get("candidate_id") == candidate_id:
            stamp = obj.get("decision_timestamp")
            try:
                order = float(stamp)
            except (TypeError, ValueError):
                order = -1.0
            matches.append((order, path.name, obj))
    matches.sort(key=lambda x: (x[0], x[1]))
    return [obj for _, _, obj in matches]


def latest_overlay(runtime_root: Path, candidate_id: str) -> dict[str, Any] | None:
    history = overlay_history(runtime_root, candidate_id)
    return history[-1] if history else None


def summarize(queue_data: dict[str, Any], runtime_root: Path) -> dict[str, Any]:
    rows = []
    for row in queue_data.get("queue", []):
        if not isinstance(row, dict):
            continue
        cid = row.get("candidate_id")
        if not isinstance(cid, str) or not cid:
            continue
        history = overlay_history(runtime_root, cid)
        overlay = history[-1] if history else None
        prebuild = _current_review(overlay, "PREBUILD")
        premeasurement = _current_review(overlay, "PREMEASUREMENT")
        measurement = {}
        if isinstance(overlay, dict) and isinstance(overlay.get("measurement_authorization"), dict):
            authorization = overlay["measurement_authorization"]
            if (
                premeasurement.get("decision") == "APPROVE"
                and authorization.get("authorized") is True
                and authorization.get("astra_premeasurement_review_ref") == premeasurement.get("ref")
            ):
                measurement = authorization
        rows.append({
            "candidate_id": cid,
            "source_queue_status": row.get("queue_status"),
            "runtime_queue_status": overlay.get("queue_status") if overlay else None,
            "finding": overlay.get("finding") if overlay else None,
            "next_action": overlay.get("next_action") if overlay else row.get("next_decisive_test"),
            "scientific_status": (overlay.get("scientific_status") if overlay else None) or "NO_PROVEN_EDGE",
            "astra_prebuild": prebuild.get("decision"),
            "astra_premeasurement": premeasurement.get("decision"),
            "measurement_scope": measurement.get("scope"),
            "measurement_order_submission": measurement.get("order_submission"),
        })
    return {
        "candidate_count": len(rows),
        "candidates": rows,
        "economic_conclusion": "NO_PROVEN_EDGE",
    }


def render(summary: dict[str, Any]) -> str:
    lines = [MARKER, "", "Economic conclusion: **NO_PROVEN_EDGE**", ""]
    rows = summary.get("candidates", [])
    if not rows:
        lines.append("No active candidate outcomes available.")
        return "\n".join(lines) + "\n"
    for row in rows:
        lines.append(f"### {row['candidate_id']}")
        lines.append(f"- Source queue: {row.get('source_queue_status')}")
        lines.append(f"- Runtime result: {row.get('runtime_queue_status') or 'NO_RUNTIME_RESULT'}")
        lines.append(f"- Scientific status: {row.get('scientific_status') or 'NO_PROVEN_EDGE'}")
        if row.get("astra_prebuild"):
            lines.append(f"- Astra pre-build: {row['astra_prebuild']}")
        if row.get("astra_premeasurement"):
            lines.append(f"- Astra pre-measurement: {row['astra_premeasurement']}")
        if row.get("measurement_scope"):
            lines.append(f"- Measurement scope: {row['measurement_scope']}")
            lines.append(f"- Order submission: {row.get('measurement_order_submission')}")
        if row.get("finding"):
            lines.append(f"- Finding: {row['finding']}")
        if row.get("next_action"):
            lines.append(f"- Next action: {row['next_action']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def append_to_report(report_path: Path, queue_data: dict[str, Any], runtime_root: Path) -> dict[str, Any]:
    report_path = Path(report_path)
    summary = summarize(queue_data, runtime_root)
    section = render(summary)
    existing = report_path.read_text(encoding="utf-8", errors="replace") if report_path.exists() else ""
    if MARKER in existing:
        existing = existing.split(MARKER, 1)[0].rstrip() + "\n\n"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(existing + section, encoding="utf-8")
    return summary
