from __future__ import annotations

from pathlib import Path
import hashlib
import json
import sys

ROUTE_TASK = "DEV-PRED-CONT-NEXT-9bc61d67f5718acd295626c7"


def pre() -> None:
    cfg = json.loads(Path("knowledge/codex_runtime/CONFIG.json").read_text())
    mapping = {
        "supervisor_sha256": "control/codex_supervisor/supervisor.py",
        "candidate_dispatch.py_sha256": "control/codex_supervisor/candidate_dispatch.py",
        "build_wake.py_sha256": "control/codex_supervisor/build_wake.py",
        "evidence_wake.py_sha256": "control/codex_supervisor/evidence_wake.py",
        "candidate_policy_sha256": "control/hourly/candidate_queue.py",
    }
    bad = []
    for key, rel in mapping.items():
        actual = hashlib.sha256(Path(rel).read_bytes()).hexdigest()
        if cfg.get(key) != actual:
            bad.append((key, cfg.get(key), actual))
    if bad:
        raise SystemExit("AUTOBUILD_PIN_CHECK_FAIL=" + repr(bad))
    print("AUTOBUILD_PIN_CHECK=PASS", flush=True)


def post() -> None:
    runtime = Path.home() / ".local/share/prediction-chat-bridge"
    cm = (runtime / "continuation_manager.py").read_text()
    assert "def start_external_continuation(" in cm
    assert "context_message" in cm
    route = json.loads((runtime / "autobuild_control_route.json").read_text())
    assert route["schema"] == "PREDICTION_AUTOBUILD_ROUTE_V1"
    assert route["route_task_id"] == ROUTE_TASK
    binding = json.loads((runtime / "routes" / f"{ROUTE_TASK}.json").read_text())
    assert binding.get("task_id") == ROUTE_TASK
    assert isinstance(binding.get("chat_id"), str) and len(binding["chat_id"]) >= 4
    print("AUTOBUILD_INSTALLED_RUNTIME=PASS route_task_id=" + ROUTE_TASK, flush=True)


def canary() -> None:
    sys.path.insert(0, str(Path("control/codex_supervisor").resolve()))
    import build_wake

    class Supervisor:
        def __init__(self, root: Path):
            self.root = root

    candidate_path = Path("knowledge/candidates/__AUTOBUILD_CANARY_20261003_E042.json")
    candidate = {
        "candidate_id": "AUTOBUILD_CANARY_20261003_E042",
        "queue_status": "NEEDS_BUILD",
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "prospective_protocols": [],
    }
    candidate_path.write_text(json.dumps(candidate, sort_keys=True) + "\n", encoding="utf-8")
    source_sha = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    overlay = {
        "candidate_id": candidate["candidate_id"],
        "queue_status": "NEEDS_BUILD",
        "source_hashes": {candidate_path.as_posix(): source_sha},
        "originating_task_id": "AUTOBUILD-CANARY-ORIGIN-20261003-E042",
        "completion_hash": "c" * 64,
        "finding": "Synthetic transport canary; implementation is already under acceptance test and no additional candidate code change is required.",
        "next_action": "Confirm the autonomous autobuild wake reaches the bound ChatGPT session; then choose DONE for this synthetic canary.",
        "candidate_snapshot": candidate,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
    }
    root = Path("control/dev_checks/autobuild_canary_runtime_e042")
    root.mkdir(parents=True, exist_ok=True)
    result = build_wake.ensure_build_continuation(Supervisor(root), overlay)
    bridge = Path.home() / ".local/share/prediction-chat-bridge"
    record = json.loads((bridge / "continuations" / f"{result['continuation_id']}.json").read_text())
    assert record["external_source"] is True
    assert record["external_source_kind"] == "AUTOBUILD"
    assert record["expected_route_task_id"] == ROUTE_TASK
    assert candidate["candidate_id"] in record["context_message"]
    assert "live_trading:false" in record["context_message"]
    print("AUTOBUILD_SYNTHETIC_WAKE=PASS continuation_id=" + result["continuation_id"], flush=True)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "pre":
        pre()
    elif mode == "post":
        post()
    elif mode == "canary":
        canary()
    else:
        raise SystemExit("usage: autobuild_acceptance_e042.py pre|post|canary")
