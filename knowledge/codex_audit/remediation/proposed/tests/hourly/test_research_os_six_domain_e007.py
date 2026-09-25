from __future__ import annotations

from pathlib import Path
import importlib.util
import json
import sys


ROOT = Path.cwd()


def load(name: str, relative: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def write_packet(run: Path, role: str, **extra):
    payload = {
        "agent_id": role,
        "run_id": run.name,
        "status": "READY",
        "input_refs": [],
        "candidate_ids": [],
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "openai_api": False,
    }
    payload.update(extra)
    (run / f"{role}.json").write_text(json.dumps(payload))


def test_registry_has_exactly_six_permanent_agents_and_transient_reproducer():
    registry = json.loads((ROOT / "agents/registry.json").read_text())
    permanent = [row["id"] for row in registry["roles"]]
    transient = [row["id"] for row in registry["transient_roles"]]

    assert permanent == [
        "discovery",
        "market_research",
        "mechanics",
        "algebra",
        "red_team_pentest",
        "research_director",
    ]
    assert transient == ["independent_reproducer"]
    assert registry["version"] == 4
    assert registry["live_trading"] is False
    assert registry["paid_actions"] is False
    assert registry["wallet_actions"] is False


def test_legacy_specialists_are_capabilities_not_permanent_agents():
    arch = load("e007_architecture_mapping", "control/hourly/research_os_architecture.py")
    assert arch.domain_for_capability("scout") == "discovery"
    assert arch.domain_for_capability("recon_scout") == "discovery"
    assert arch.domain_for_capability("weather_twc") == "market_research"
    assert arch.domain_for_capability("behavioral") == "market_research"
    assert arch.domain_for_capability("informed_flow") == "market_research"
    assert arch.domain_for_capability("settlement") == "mechanics"
    assert arch.domain_for_capability("microstructure") == "mechanics"
    assert arch.domain_for_capability("prebuild_killer") == "red_team_pentest"
    assert arch.domain_for_capability("chief_falsifier") == "red_team_pentest"
    assert arch.PROTECTED_DISCOVERY_LANES == ("primary_scout", "recon_scout")


def test_real_semantics_route_into_domain_capability_buckets(tmp_path):
    router = load("e007_candidate_router", "control/hourly/candidate_worker_routing.py")
    run = tmp_path / "hourly-test"
    run.mkdir()
    for role in (
        "discovery",
        "market_research",
        "mechanics",
        "algebra",
        "red_team_pentest",
        "research_director",
    ):
        write_packet(run, role, status="PENDING")

    rows = [
        {
            "candidate_id": "WEATHER-X",
            "phase": "DISCOVERED",
            "queue_status": "NEEDS_DIRECTOR",
            "routing_metadata": {
                "lane": "WEATHER",
                "hypothesis": "KWI station temperature may lead TWC temperature publication",
                "required_checks": ["settlement source finality"],
            },
        },
        {
            "candidate_id": "PAYOFF-X",
            "phase": "MECHANISM_DEFINED",
            "queue_status": "RUNNING",
            "routing_metadata": {
                "lane": "MARKET_ALGEBRA",
                "hypothesis": "statewise payoff identity",
                "required_data": ["executable L2 depth and slippage"],
            },
        },
    ]

    assignments = router.hydrate_candidate_routes(run, {"queue": rows})
    assignment_keys = {
        (row["candidate_id"], row["role"], row["capability"])
        for row in assignments
    }

    assert ("WEATHER-X", "market_research", "weather_twc") in assignment_keys
    assert ("WEATHER-X", "mechanics", "settlement") in assignment_keys
    assert ("PAYOFF-X", "algebra", "algebra") in assignment_keys
    assert ("PAYOFF-X", "mechanics", "microstructure") in assignment_keys
    assert ("WEATHER-X", "red_team_pentest", "prebuild_killer") in assignment_keys
    assert ("PAYOFF-X", "red_team_pentest", "prebuild_killer") in assignment_keys

    market = json.loads((run / "market_research.json").read_text())
    mechanics = json.loads((run / "mechanics.json").read_text())
    red = json.loads((run / "red_team_pentest.json").read_text())

    assert market["capability_work"]["weather_twc"]["candidate_ids"] == ["WEATHER-X"]
    assert set(mechanics["candidate_ids"]) == {"PAYOFF-X", "WEATHER-X"}
    assert set(red["candidate_ids"]) == {"PAYOFF-X", "WEATHER-X"}
    assert red["red_team_modes"] == {
        "PAYOFF-X": "QUICK_KILL",
        "WEATHER-X": "QUICK_KILL",
    }


def test_scheduler_caps_permanent_specialists_at_five_and_isolates_reproducer(tmp_path):
    scheduler = load("e007_task_scheduler", "control/hourly/task_shape_scheduler.py")
    run = tmp_path / "hourly-test"
    run.mkdir()

    for role in (
        "discovery",
        "market_research",
        "mechanics",
        "algebra",
        "red_team_pentest",
        "research_director",
    ):
        write_packet(run, role, candidate_ids=[role + "-CAND"] if role != "research_director" else [])

    write_packet(
        run,
        "independent_reproducer",
        candidate_ids=["SERIOUS"],
        reproduction_candidates=["SERIOUS"],
        transient=True,
        blind=True,
    )

    out = scheduler.schedule(run)
    assert len(out["scheduled_dynamic_workers"]) == 5
    assert set(out["scheduled_dynamic_workers"]) == {
        "discovery",
        "market_research",
        "mechanics",
        "algebra",
        "red_team_pentest",
    }
    assert out["scheduled_transient_workers"] == ["independent_reproducer"]
    assert "research_director" not in out["scheduled_dynamic_workers"]

    reproducer = json.loads((run / "independent_reproducer.json").read_text())
    assert reproducer["isolated_validation_worker"] is True
    assert reproducer["blind"] is True
    assert reproducer["task_shape"]["name"] == "LOW_SEQUENTIAL"
    assert reproducer["task_shape"]["max_parallel_workers"] == 1


def test_evidence_failure_graph_seeds_36_patterns_and_preserves_negative_result(tmp_path):
    graph = load("e007_evidence_failure_graph", "control/hourly/evidence_failure_graph.py")
    store = tmp_path / "knowledge/research_os"
    graph.ROOT = tmp_path
    graph.STORE = store
    graph.EVIDENCE_PATH = store / "evidence_graph.json"
    graph.FAILURE_PATH = store / "failure_graph.json"

    assert len(graph.FAILURE_PATTERNS) == 36
    assert graph.FAILURE_PATTERNS["FP-001"] == "SAME_TITLE_NOT_SAME_CONTRACT"
    assert graph.FAILURE_PATTERNS["FP-036"] == "ZOMBIE_CANDIDATE"

    response = {
        "role_results": [{
            "agent_id": "red_team_pentest",
            "status": "FALSIFIED",
            "finding": "FP-007 GROSS_EDGE_DIES_AFTER_FRICTION",
            "candidate_ids": ["CAND-X"],
            "evidence_refs": ["knowledge/test.json"],
            "capability_results": {},
            "validation_results": [{
                "candidate_id": "CAND-X",
                "status": "FAIL",
                "mode": "QUICK_KILL",
            }],
        }],
        "candidate_decisions": [{
            "candidate_id": "CAND-X",
            "queue_status": "PARKED",
            "reason": "gross edge disappears after executable friction",
            "resurrection_condition": "fee or spread regime changes materially",
        }],
    }

    graph.record_ai_response("hourly-test", response)
    failure = json.loads(graph.FAILURE_PATH.read_text())

    assert failure["patterns"]["FP-007"]["candidate_ids"] == ["CAND-X"]
    negatives = list(failure["negative_results"].values())
    assert len(negatives) == 1
    assert negatives[0]["candidate_id"] == "CAND-X"
    assert negatives[0]["resurrection_condition"] == "fee or spread regime changes materially"


def test_research_os_graphs_are_durable_checkpoint_state():
    checkpoint = load("e007_checkpoint", "control/hourly/git_checkpoint.py")
    for path in (
        "knowledge/research_os/evidence_graph.json",
        "knowledge/research_os/failure_graph.json",
    ):
        assert checkpoint.matches_allow(path) is True
        assert checkpoint.denied(path) is False
