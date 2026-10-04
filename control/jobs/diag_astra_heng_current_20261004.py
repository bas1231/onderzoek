from __future__ import annotations
import json, pathlib, time

PROD = pathlib.Path("/home/leonh/prediction_research_prod")
RUNTIME = PROD / "knowledge" / "codex_runtime"
CID = "MANUAL-SCOUT-HENGELTJES-20260924"
BRIDGE = pathlib.Path.home() / ".local" / "share" / "prediction-chat-bridge"

def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_error": type(exc).__name__, "_path": str(path)}

def main():
    out = {
        "checked_at": time.time(),
        "supervisor_state": load(RUNTIME / "STATE.json") if (RUNTIME / "STATE.json").exists() else None,
        "active_goal": (RUNTIME / "ACTIVE_GOAL.md").read_text(encoding="utf-8")[:4000] if (RUNTIME / "ACTIVE_GOAL.md").exists() else None,
        "heng_overlays": [],
        "astra_reviews": [],
        "astra_review_wakes": [],
        "autobuild_wakes": [],
        "measurement_wakes": [],
        "continuations": [],
    }

    state_root = RUNTIME / "candidate_states"
    if state_root.exists():
        for p in sorted(state_root.glob("*.json")):
            obj = load(p)
            if isinstance(obj, dict) and obj.get("candidate_id") == CID:
                out["heng_overlays"].append({
                    "path": str(p),
                    "queue_status": obj.get("queue_status"),
                    "finding": obj.get("finding"),
                    "next_action": obj.get("next_action"),
                    "scientific_status": obj.get("scientific_status"),
                    "decision_timestamp": obj.get("decision_timestamp"),
                    "originating_task_id": obj.get("originating_task_id"),
                    "completion_hash": obj.get("completion_hash"),
                    "validation_hash": obj.get("validation_hash"),
                    "astra_gate": obj.get("astra_gate"),
                    "astra_reviews": obj.get("astra_reviews"),
                    "pending_build_handoff": obj.get("pending_build_handoff"),
                    "build_handoff": obj.get("build_handoff"),
                    "measurement_authorization": obj.get("measurement_authorization"),
                    "activation": obj.get("activation"),
                })

    reviews_root = PROD / "knowledge" / "reviews" / "astra"
    if reviews_root.exists():
        for p in sorted(reviews_root.glob(f"{CID}-*.json")):
            out["astra_reviews"].append({"path": str(p.relative_to(PROD)), "review": load(p)})

    for key, dirname in [
        ("astra_review_wakes", "astra_review_wakes"),
        ("autobuild_wakes", "autobuild_wakes"),
        ("measurement_wakes", "measurement_wakes"),
    ]:
        root = RUNTIME / dirname
        if root.exists():
            for p in sorted(root.glob("*.json")):
                obj = load(p)
                if isinstance(obj, dict) and obj.get("candidate_id") == CID:
                    out[key].append({"path": str(p), "data": obj})

    cont_root = BRIDGE / "continuations"
    if cont_root.exists():
        for p in sorted(cont_root.glob("CONT-*.json")):
            obj = load(p)
            if not isinstance(obj, dict):
                continue
            msg = str(obj.get("context_message") or "")
            if CID in msg:
                out["continuations"].append({
                    "path": str(p),
                    "continuation_id": obj.get("continuation_id"),
                    "source_task_id": obj.get("source_task_id"),
                    "external_source_kind": obj.get("external_source_kind"),
                    "state": obj.get("state"),
                    "attempts": obj.get("attempts"),
                    "expected_next_task_id": obj.get("expected_next_task_id"),
                    "expected_done_task_id": obj.get("expected_done_task_id"),
                    "expected_blocked_task_id": obj.get("expected_blocked_task_id"),
                    "updated_at": obj.get("updated_at"),
                    "history": obj.get("history", [])[-8:],
                    "context_message": msg[:2500],
                })

    print(json.dumps(out, ensure_ascii=False, sort_keys=True))

if __name__ == "__main__":
    main()
