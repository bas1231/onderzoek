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


def load_module(name: str, relative: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def write_packets(run: Path, *, evidence_role: str | None = None) -> None:
    run.mkdir(parents=True, exist_ok=True)
    for role in PRIMARY_ROLES:
        (run / f"{role}.json").write_text(json.dumps({
            "agent_id": role,
            "status": "PENDING",
            "input_refs": ["routing.json"] if role == evidence_role else [],
            "live_trading": True,
            "paid_actions": True,
            "wallet_actions": True,
            "openai_api": True,
        }))


def row(
    candidate_id: str,
    *,
    lane: str,
    queue_status: str = "NEEDS_DIRECTOR",
    phase: str = "DISCOVERED",
    hypothesis: str = "",
    mechanism: str = "",
    next_decisive_test: str | None = None,
    required_data=None,
    required_tests=None,
    required_clean_room_checks=None,
):
    return {
        "candidate_id": candidate_id,
        "phase": phase,
        "queue_status": queue_status,
        "priority": "P2",
        "open_question": None,
        "next_decisive_test": next_decisive_test,
        "routing_metadata": {
            "candidate_id": candidate_id,
            "lane": lane,
            "hypothesis": hypothesis,
            "mechanism": mechanism,
            "next_decisive_test": next_decisive_test,
            "required_data": required_data or [],
            "required_tests": required_tests or [],
            "required_clean_room_checks": required_clean_room_checks or [],
        },
    }


def packet(run: Path, role: str):
    return json.loads((run / f"{role}.json").read_text())


def test_weather_candidate_routes_to_weather_and_material_settlement(tmp_path):
    orchestrator = load_module(
        "agent_orchestrator_e006_weather",
        "control/hourly/agent_orchestrator.py",
    )
    run = tmp_path / "run"
    write_packets(run)
    candidate = row(
        "KWI-TEST",
        lane="WEATHER",
        hypothesis="Incomplete KWI station observations may predict TWC temperature.",
        required_clean_room_checks=["settlement_required"],
    )

    result = orchestrator.orchestrate(run, candidate_queue={"queue": [candidate]})

    assert packet(run, "weather_twc")["candidate_ids"] == ["KWI-TEST"]
    assert packet(run, "settlement")["candidate_ids"] == ["KWI-TEST"]
    assert packet(run, "weather_twc")["status"] == "READY"
    assert packet(run, "algebra").get("candidate_ids", []) == []
    routes = {(x["candidate_id"], x["role"]) for x in result["candidate_routing"]}
    assert ("KWI-TEST", "weather_twc") in routes
    assert ("KWI-TEST", "settlement") in routes


def test_payoff_identity_routes_to_algebra_and_only_justified_extras(tmp_path):
    orchestrator = load_module(
        "agent_orchestrator_e006_identity",
        "control/hourly/agent_orchestrator.py",
    )
    run = tmp_path / "run"
    write_packets(run)
    candidate = row(
        "PAYOFF-ID-TEST",
        lane="ALGEBRA",
        hypothesis="Different contract paths can have identical statewise payoff identity.",
        mechanism="Prove equivalence before price comparison.",
        required_data=["simultaneous executable L2 depth and slippage"],
        required_tests=["settlement source and settlement transformation identity"],
    )

    orchestrator.orchestrate(run, candidate_queue={"queue": [candidate]})

    assert packet(run, "algebra")["candidate_ids"] == ["PAYOFF-ID-TEST"]
    assert packet(run, "microstructure")["candidate_ids"] == ["PAYOFF-ID-TEST"]
    assert packet(run, "settlement")["candidate_ids"] == ["PAYOFF-ID-TEST"]
    for unrelated in ("weather_twc", "behavioral", "informed_flow", "scout", "recon_scout"):
        assert packet(run, unrelated).get("candidate_ids", []) == []


def test_maker_hedge_routes_to_microstructure_and_algebra_not_weather(tmp_path):
    orchestrator = load_module(
        "agent_orchestrator_e006_maker",
        "control/hourly/agent_orchestrator.py",
    )
    run = tmp_path / "run"
    write_packets(run)
    candidate = row(
        "MAKER-HEDGE-TEST",
        lane="ALGEBRA",
        phase="MECHANISM_DEFINED",
        queue_status="RUNNING",
        mechanism=(
            "Passive maker fill on one leg followed by taker hedge on the other "
            "legs can complete a one-hot partition."
        ),
        required_data=["depth-5 orderbook", "fill probability", "hedge latency and slippage"],
    )

    orchestrator.orchestrate(run, candidate_queue={"queue": [candidate]})

    assert packet(run, "algebra")["candidate_ids"] == ["MAKER-HEDGE-TEST"]
    assert packet(run, "microstructure")["candidate_ids"] == ["MAKER-HEDGE-TEST"]
    assert packet(run, "weather_twc").get("candidate_ids", []) == []
    assert packet(run, "scout").get("candidate_ids", []) == []


def test_routing_is_deterministic_and_deduplicated(tmp_path):
    orchestrator = load_module(
        "agent_orchestrator_e006_dedup",
        "control/hourly/agent_orchestrator.py",
    )
    first = row(
        "PAYOFF-DUP",
        lane="ALGEBRA",
        hypothesis="statewise payoff identity",
    )
    duplicate = json.loads(json.dumps(first))

    outputs = []
    for index, rows in enumerate(([first, duplicate], [duplicate, first])):
        run = tmp_path / f"run-{index}"
        write_packets(run)
        result = orchestrator.orchestrate(run, candidate_queue={"queue": rows})
        outputs.append(result["candidate_routing"])
        assert packet(run, "algebra")["candidate_ids"] == ["PAYOFF-DUP"]
        assert len(packet(run, "algebra")["candidate_routing"]) == 1

    assert outputs[0] == outputs[1]
    assert [x for x in outputs[0] if x["role"] == "algebra"] == [
        x for x in outputs[1] if x["role"] == "algebra"
    ]


def test_routed_evidence_only_flow_and_empty_queue_remain_unchanged(tmp_path):
    orchestrator = load_module(
        "agent_orchestrator_e006_evidence",
        "control/hourly/agent_orchestrator.py",
    )
    run = tmp_path / "run"
    write_packets(run, evidence_role="settlement")

    result = orchestrator.orchestrate(run, candidate_queue={"queue": []})

    assert packet(run, "settlement")["status"] == "READY"
    assert packet(run, "settlement")["orchestrator_reason"] == "routed_evidence_available"
    assert packet(run, "settlement").get("candidate_ids", []) == []
    assert result["candidate_routing"] == []


def test_terminal_and_parked_candidates_are_not_reactivated(tmp_path):
    orchestrator = load_module(
        "agent_orchestrator_e006_terminal",
        "control/hourly/agent_orchestrator.py",
    )
    run = tmp_path / "run"
    write_packets(run)
    closed = row("CLOSED", lane="WEATHER", queue_status="CLOSED_NEGATIVE")
    parked = row("PARKED", lane="ALGEBRA", queue_status="PARKED", hypothesis="payoff identity")

    result = orchestrator.orchestrate(
        run,
        candidate_queue={"queue": [closed, parked]},
    )

    assert result["candidate_routing"] == []
    for role in PRIMARY_ROLES:
        assert packet(run, role).get("candidate_ids", []) == []
        assert packet(run, role)["status"] == "NO_EVIDENCE"


def test_candidate_routing_keeps_all_safety_flags_false(tmp_path):
    orchestrator = load_module(
        "agent_orchestrator_e006_safety",
        "control/hourly/agent_orchestrator.py",
    )
    run = tmp_path / "run"
    write_packets(run)
    candidate = row("SAFE-WEATHER", lane="WEATHER", hypothesis="KWI temperature")

    result = orchestrator.orchestrate(run, candidate_queue={"queue": [candidate]})
    routed = packet(run, "weather_twc")

    for key in ("live_trading", "paid_actions", "wallet_actions", "openai_api"):
        assert routed[key] is False
        assert result["guardrails"][key] is False


def test_hourly_cycle_builds_one_queue_snapshot_before_orchestration():
    source = (ROOT / "control/hourly/hourly_cycle.py").read_text()
    queue_pos = source.index("queue_data = candidate_queue.build_queue")
    hydrate_pos = source.index("hydrator.hydrate_run")
    orchestrate_pos = source.index("orchestrator.orchestrate")
    handoff_pos = source.index("candidate_queue.write_handoff")

    assert source.count("candidate_queue.build_queue(") == 1
    assert queue_pos < hydrate_pos < orchestrate_pos < handoff_pos
    assert "candidate_queue=queue_data" in source


def test_synthetic_candidate_ids_survive_into_exchange_work_items(tmp_path):
    orchestrator = load_module(
        "agent_orchestrator_e006_exchange",
        "control/hourly/agent_orchestrator.py",
    )
    ai_handoff = load_module(
        "ai_handoff_e006_exchange",
        "control/hourly/ai_handoff.py",
    )
    exchange = load_module(
        "ai_work_exchange_e006_exchange",
        "control/hourly/ai_work_exchange.py",
    )

    candidates = [
        row(
            "WEATHER-CANARY",
            lane="WEATHER",
            hypothesis="KWI station temperature may lead TWC publication.",
        ),
        row(
            "PAYOFF-CANARY",
            lane="ALGEBRA",
            hypothesis="statewise payoff identity may create equivalent portfolios",
            required_data=["simultaneous executable L2 depth"],
        ),
        row(
            "MAKER-CANARY",
            lane="MICROSTRUCTURE",
            phase="MECHANISM_DEFINED",
            queue_status="RUNNING",
            mechanism="maker fill followed by taker hedge",
            required_data=["fill probability", "slippage", "hedge latency"],
        ),
    ]

    run = tmp_path / "fresh-canary"
    write_packets(run)
    result = orchestrator.orchestrate(run, candidate_queue={"queue": candidates})

    assert packet(run, "weather_twc")["candidate_ids"] == ["WEATHER-CANARY"]
    assert "PAYOFF-CANARY" in packet(run, "algebra")["candidate_ids"]
    assert "PAYOFF-CANARY" in packet(run, "microstructure")["candidate_ids"]
    assert "MAKER-CANARY" in packet(run, "microstructure")["candidate_ids"]
    assert packet(run, "scout").get("candidate_ids", []) == []
    assert packet(run, "recon_scout").get("candidate_ids", []) == []

    ready_roles = []
    for role in PRIMARY_ROLES:
        data = packet(run, role)
        if data["status"] == "READY":
            ready_roles.append(ai_handoff.compact_packet(data))

    bundle = {
        "schema": "PVA_AI_WORK_BUNDLE_V1",
        "run_id": "hourly-20990101T000000+0000",
        "response_token": "a" * 64,
        "created_at": "2099-01-01T00:00:00+00:00",
        "guardrails": {
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "openai_api": False,
        },
        "ready_roles": ready_roles,
        "candidate_queue": {
            "full_queue": candidates,
            "director_attention": candidates,
            "waiting_without_blocking": [],
        },
        "director_instruction": "candidate routing regression",
        "expected_response_schema": {},
    }
    request = exchange.build_request(bundle, source_commit="0" * 40)
    work_by_role = {x["agent_id"]: x for x in request["work_items"]}

    assert "WEATHER-CANARY" in work_by_role["weather_twc"]["packet"]["candidate_ids"]
    assert "PAYOFF-CANARY" in work_by_role["algebra"]["packet"]["candidate_ids"]
    assert "MAKER-CANARY" in work_by_role["microstructure"]["packet"]["candidate_ids"]
    assert result["validation_pipeline"]["proof_candidates"] == []
    assert request["governor"]["ai_candidate_promotion_authority"] is False
    assert request["governor"]["ai_candidate_kill_authority"] is False
    assert request["governor"]["economic_conclusion"] == "NO_PROVEN_EDGE"
