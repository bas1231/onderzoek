from __future__ import annotations

from pathlib import Path
from typing import Any
import json

MARKER = "## Candidate outcomes"


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return value if isinstance(value, dict) else None


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
        prebuild = {}
        premeasurement = {}
        measurement = {}
        for item in history:
            reviews = item.get("astra_reviews", {})
            if isinstance(reviews, dict):
                if isinstance(reviews.get("PREBUILD"), dict):
                    prebuild = reviews["PREBUILD"]
                if isinstance(reviews.get("PREMEASUREMENT"), dict):
                    premeasurement = reviews["PREMEASUREMENT"]
            if isinstance(item.get("measurement_authorization"), dict):
                measurement = item["measurement_authorization"]
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
