from __future__ import annotations

from pathlib import Path
import importlib.util
import json
import sys


ROOT = Path.cwd()
PRIMARY_ROLES = [
    "recon_scout",
    "scout",
    "algebra",
    "settlement",
    "microstructure",
    "behavioral",
    "informed_flow",
    "weather_twc",
]
CURRENT_CANDIDATES = {
    "KWI-INCOMPLETE-TO-CANONICAL-V1",
    "PAYOFF-IDENTITY-MINING-V1",
    "ASSET-RANK-MAKER-HEDGE-V1",
    "KWI-FULL-STATION-PRECANONICAL-V1",
}


def load_module(name: str, relative: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def write_primary_packets(packet_dir: Path) -> None:
    packet_dir.mkdir(parents=True, exist_ok=True)
    for role in PRIMARY_ROLES:
        (packet_dir / f"{role}.json").write_text(json.dumps({
            "agent_id": role,
            "status": "PENDING",
            "input_refs": [],
            "contract": {"agent": role},
            "live_trading": True,
            "paid_actions": True,
            "wallet_actions": True,
            "openai_api": True,
        }))


def test_e006_current_candidates_reach_real_bundle_and_exchange_request(tmp_path):
    orchestrator = load_module(
        "agent_orchestrator_e006_canary",
        "control/hourly/agent_orchestrator.py",
    )
    candidate_queue = load_module(
        "candidate_queue_e006_canary",
        "control/hourly/candidate_queue.py",
    )
    ai_handoff = load_module(
        "ai_handoff_e006_canary",
        "control/hourly/ai_handoff.py",
    )
    exchange = load_module(
        "ai_work_exchange_e006_canary",
        "control/hourly/ai_work_exchange.py",
    )

    run_id = "hourly-20990101T000000+0000"
    runs_root = tmp_path / "knowledge/runs"
    packets_root = runs_root / "agent_packets"
    packet_dir = packets_root / run_id
    write_primary_packets(packet_dir)

    queue = candidate_queue.build_queue(write_candidates=False)
    queue_ids = {str(row.get("candidate_id")) for row in queue["queue"]}
    assert CURRENT_CANDIDATES <= queue_ids

    orchestration = orchestrator.orchestrate(
        packet_dir,
        candidate_queue=queue,
    )

    def packet(role: str):
        return json.loads((packet_dir / f"{role}.json").read_text())

    weather_ids = set(packet("weather_twc").get("candidate_ids", []))
    algebra_ids = set(packet("algebra").get("candidate_ids", []))
    micro_ids = set(packet("microstructure").get("candidate_ids", []))
    settlement_ids = set(packet("settlement").get("candidate_ids", []))

    assert "KWI-INCOMPLETE-TO-CANONICAL-V1" in weather_ids
    assert "KWI-FULL-STATION-PRECANONICAL-V1" in weather_ids
    assert "PAYOFF-IDENTITY-MINING-V1" in algebra_ids
    assert "ASSET-RANK-MAKER-HEDGE-V1" in algebra_ids
    assert "PAYOFF-IDENTITY-MINING-V1" in micro_ids
    assert "ASSET-RANK-MAKER-HEDGE-V1" in micro_ids
    assert "PAYOFF-IDENTITY-MINING-V1" in settlement_ids

    # Specialist candidates must not leak back into generic discovery or
    # unrelated behavioral/flow roles merely because their phase is DISCOVERED.
    for unrelated in ("scout", "recon_scout", "behavioral", "informed_flow"):
        assert not (set(packet(unrelated).get("candidate_ids", [])) & CURRENT_CANDIDATES)

    # Every assignment is auditable and routing itself does not manufacture a
    # proof candidate or mutate the candidate lifecycle.
    assert orchestration["candidate_routing"]
    assert all(item.get("reasons") for item in orchestration["candidate_routing"])
    assert orchestration["validation_pipeline"]["proof_candidates"] == []
    assert orchestration["validation_pipeline"]["economic_conclusion"] == "NO_PROVEN_EDGE"

    # Build the actual PVA_AI_WORK_BUNDLE_V1 from the freshly routed packets.
    ai_handoff.RUNS = runs_root
    ai_handoff.PACKETS = packets_root
    handoff = {
        "run_id": run_id,
        "director_attention": [
            row for row in queue["queue"]
            if row["queue_status"] in {
                "NEEDS_DIRECTOR",
                "RESULT_READY",
                "NEEDS_REVISION",
                "PROMOTION_CANDIDATE",
                "EXPERIMENT_REQUIRED",
            }
        ],
        "waiting_without_blocking": [
            row for row in queue["queue"]
            if row["queue_status"] in {
                "RUNNING",
                "WAITING_FOR_DATA",
                "WAITING_FOR_RESULT",
            }
        ],
        "full_queue": queue["queue"],
    }
    (runs_root / f"{run_id}-director-handoff.json").write_text(
        json.dumps(handoff, indent=2, sort_keys=True) + "\n"
    )

    bundle, bundle_path = ai_handoff.build(run_id)
    assert bundle_path.exists()
    bundle_by_role = {row["agent_id"]: row for row in bundle["ready_roles"]}
    assert "KWI-INCOMPLETE-TO-CANONICAL-V1" in bundle_by_role["weather_twc"]["candidate_ids"]
    assert "PAYOFF-IDENTITY-MINING-V1" in bundle_by_role["algebra"]["candidate_ids"]
    assert "ASSET-RANK-MAKER-HEDGE-V1" in bundle_by_role["microstructure"]["candidate_ids"]

    # The exact same queue snapshot remains visible to the Director, including
    # candidate-specific next steps where the canonical record has one.
    bundle_queue = {
        row["candidate_id"]: row
        for row in bundle["candidate_queue"]["full_queue"]
    }
    assert set(bundle_queue) >= CURRENT_CANDIDATES
    assert bundle_queue["ASSET-RANK-MAKER-HEDGE-V1"]["next_decisive_test"]
    assert bundle_queue["KWI-FULL-STATION-PRECANONICAL-V1"]["next_decisive_test"]

    # Build the real transport-neutral request; packet candidate IDs must
    # survive unchanged into the work_items offered to the AI worker.
    request = exchange.build_request(bundle, source_commit="0" * 40)
    request_by_role = {row["agent_id"]: row for row in request["work_items"]}
    assert "KWI-INCOMPLETE-TO-CANONICAL-V1" in request_by_role["weather_twc"]["packet"]["candidate_ids"]
    assert "PAYOFF-IDENTITY-MINING-V1" in request_by_role["algebra"]["packet"]["candidate_ids"]
    assert "ASSET-RANK-MAKER-HEDGE-V1" in request_by_role["microstructure"]["packet"]["candidate_ids"]

    governor = request["governor"]
    assert governor["economic_conclusion"] == "NO_PROVEN_EDGE"
    assert governor["ai_candidate_promotion_authority"] is False
    assert governor["ai_candidate_kill_authority"] is False
    for key in ("live_trading", "paid_actions", "wallet_actions", "openai_api"):
        assert governor[key] is False
