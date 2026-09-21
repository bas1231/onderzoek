from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json


ROOT = Path.cwd()
CANDIDATES = ROOT / "knowledge/candidates"
RUNS = ROOT / "knowledge/runs"

QUEUE_STATES = {
    "QUEUED",
    "NEEDS_DIRECTOR",
    "EXPERIMENT_REQUIRED",
    "RUNNING",
    "WAITING_FOR_DATA",
    "WAITING_FOR_RESULT",
    "RESULT_READY",
    "NEEDS_REVISION",
    "PARKED",
    "CLOSED_NEGATIVE",
    "PROMOTION_CANDIDATE",
}

TERMINAL_QUEUE_STATES = {
    "CLOSED_NEGATIVE",
}

PRIORITY_ORDER = {
    "P0": 0,
    "P1": 1,
    "P2": 2,
    "P3": 3,
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, obj: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(obj, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def infer_queue_status(candidate: dict[str, Any]) -> str:
    existing = candidate.get("queue_status")
    if existing in QUEUE_STATES:
        return existing

    decision = str(candidate.get("decision", "")).upper()
    phase = str(candidate.get("phase", "")).upper()

    # Never infer a negative terminal state merely from age/capacity.
    if decision in {
        "FALSIFIED",
        "TESTED_NEGATIVE",
        "CLOSED_NEGATIVE",
    }:
        return "CLOSED_NEGATIVE"

    monitoring = candidate.get("prospective_monitoring")
    protocols = candidate.get("prospective_protocols") or []

    if monitoring:
        return "RUNNING"

    if protocols and phase in {
        "MECHANISM_DEFINED",
        "DATA_READY",
        "DEVELOPMENT",
        "VALIDATION",
        "HOLDOUT",
        "INDEPENDENT_REPRODUCTION",
        "EXECUTION_REALITY",
        "SHADOW",
    }:
        return "WAITING_FOR_RESULT"

    if phase == "DISCOVERED":
        return "NEEDS_DIRECTOR"

    return "QUEUED"


def infer_priority(candidate: dict[str, Any]) -> str:
    existing = candidate.get("priority")
    if existing in PRIORITY_ORDER:
        return existing

    status = infer_queue_status(candidate)

    # P1 = running/prospective evidence.
    if status in {
        "RUNNING",
        "WAITING_FOR_RESULT",
        "RESULT_READY",
    }:
        return "P1"

    # P2 = decisive Director/falsification work.
    if status in {
        "NEEDS_DIRECTOR",
        "EXPERIMENT_REQUIRED",
        "NEEDS_REVISION",
        "PROMOTION_CANDIDATE",
    }:
        return "P2"

    # Ordinary discovery/build.
    return "P3"


def candidate_timestamp(candidate: dict[str, Any]) -> str:
    return str(
        candidate.get("queue_entered_at")
        or candidate.get("updated_at")
        or candidate.get("created_at")
        or "1970-01-01T00:00:00+00:00"
    )


def age_hours(candidate: dict[str, Any]) -> float:
    raw = candidate_timestamp(candidate)

    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(
            0.0,
            (datetime.now(timezone.utc) - dt).total_seconds() / 3600,
        )
    except Exception:
        return 0.0


def effective_priority(candidate: dict[str, Any]) -> tuple[int, float, str]:
    priority = infer_priority(candidate)
    base = PRIORITY_ORDER[priority]

    # No-starvation:
    # after 24h waiting, P3 receives P2 scheduling weight.
    # after 48h waiting, P2/P3 receive P1 scheduling weight.
    # This changes scheduling order only, never candidate evidence/status.
    age = age_hours(candidate)

    effective = base

    if age >= 48 and base > 1:
        effective = 1
    elif age >= 24 and base > 2:
        effective = 2

    return (
        effective,
        -age,
        str(candidate.get("candidate_id", "")),
    )


def normalize_candidate(
    candidate: dict[str, Any],
) -> tuple[dict[str, Any], bool]:

    changed = False

    status = infer_queue_status(candidate)
    priority = infer_priority(candidate)

    if candidate.get("queue_status") != status:
        candidate["queue_status"] = status
        changed = True

    if candidate.get("priority") != priority:
        candidate["priority"] = priority
        changed = True

    if "queue_entered_at" not in candidate:
        candidate["queue_entered_at"] = (
            candidate.get("updated_at")
            or candidate.get("created_at")
            or now_iso()
        )
        changed = True

    candidate.setdefault("open_question", None)
    candidate.setdefault("next_decisive_test", None)
    candidate.setdefault("needed_data", [])
    candidate.setdefault("active_experiment_ids", [])
    candidate.setdefault("resume_condition", None)
    candidate.setdefault("stop_condition", None)

    # Guardrails are authoritative.
    if candidate.get("live_trading") is not False:
        candidate["live_trading"] = False
        changed = True

    if candidate.get("paid_actions") is not False:
        candidate["paid_actions"] = False
        changed = True

    if candidate.get("wallet_actions") is not False:
        candidate["wallet_actions"] = False
        changed = True

    return candidate, changed


def build_queue(write_candidates: bool = False) -> dict[str, Any]:
    rows = []
    modified = []

    for path in sorted(CANDIDATES.glob("*.json")):
        candidate = load_json(path)
        candidate, changed = normalize_candidate(candidate)

        if write_candidates and changed:
            save_json(path, candidate)
            modified.append(str(path.relative_to(ROOT)))

        if candidate["queue_status"] in TERMINAL_QUEUE_STATES:
            continue

        effective, neg_age, cid = effective_priority(candidate)

        rows.append({
            "candidate_id": candidate.get("candidate_id"),
            "phase": candidate.get("phase"),
            "queue_status": candidate.get("queue_status"),
            "priority": candidate.get("priority"),
            "effective_priority_rank": effective,
            "age_hours": round(-neg_age, 3),
            "open_question": candidate.get("open_question"),
            "next_decisive_test": candidate.get("next_decisive_test"),
            "active_experiment_ids": candidate.get(
                "active_experiment_ids", []
            ),
            "source_ref": str(path.relative_to(ROOT)),
        })

    rows.sort(
        key=lambda x: (
            x["effective_priority_rank"],
            -x["age_hours"],
            x["candidate_id"] or "",
        )
    )

    return {
        "generated_at": now_iso(),
        "policy": {
            "P0": "system safety; injected by control plane",
            "P1": "running/prospective evidence",
            "P2": "decisive research/falsification/reproduction",
            "P3": "discovery/build",
            "no_starvation": (
                "P3 gets P2 scheduling weight after 24h; "
                "P2/P3 get P1 scheduling weight after 48h; "
                "evidence/status is never promoted by aging"
            ),
        },
        "modified_candidates": modified,
        "queue": rows,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
    }


def write_proof_review(
    run_id: str,
    validation_pipeline: dict[str, Any],
) -> Path:
    path = RUNS / f"{run_id}-proof-review.json"
    candidates = list(validation_pipeline.get("proof_candidates", []))
    review = {
        "run_id": run_id,
        "status": "DIRECTOR_REVIEW_REQUIRED" if candidates else "NO_PROVEN_EDGE",
        "proof_candidates": candidates,
        "proof_rejections": validation_pipeline.get("proof_rejections", {}),
        "source": "agent_control_plane.validation_pipeline",
        "automatic_candidate_mutation": False,
        "automatic_proven_edge": False,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
    }
    save_json(path, review)
    return path


def write_handoff(
    queue: dict[str, Any],
    run_id: str,
    proof_review_path: Path | None = None,
) -> Path:
    path = RUNS / f"{run_id}-director-handoff.json"

    attention = [
        row for row in queue["queue"]
        if row["queue_status"] in {
            "NEEDS_DIRECTOR",
            "RESULT_READY",
            "NEEDS_REVISION",
            "PROMOTION_CANDIDATE",
            "EXPERIMENT_REQUIRED",
        }
    ]

    waiting = [
        row for row in queue["queue"]
        if row["queue_status"] in {
            "RUNNING",
            "WAITING_FOR_DATA",
            "WAITING_FOR_RESULT",
        }
    ]

    handoff = {
        "run_id": run_id,
        "generated_at": now_iso(),
        "default_economic_conclusion": "NO_PROVEN_EDGE",
        "director_attention": attention,
        "waiting_without_blocking": waiting,
        "full_queue": queue["queue"],
        "proof_review_ref": (
            str(proof_review_path.relative_to(ROOT))
            if proof_review_path is not None else None
        ),
        "guardrails": {
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
        },
    }

    save_json(path, handoff)
    return path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--run-id")
    args = parser.parse_args()

    queue = build_queue(write_candidates=args.write)

    result = {"queue": queue}

    if args.run_id:
        handoff = write_handoff(queue, args.run_id)
        result["handoff"] = str(handoff.relative_to(ROOT))

    print(json.dumps(result, indent=2, sort_keys=True))
