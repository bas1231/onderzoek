from __future__ import annotations

from pathlib import Path
import importlib.util
import sys


ROOT = Path.cwd()


def load_router():
    path = ROOT / "control/hourly/candidate_worker_routing.py"
    spec = importlib.util.spec_from_file_location(
        "candidate_worker_routing_e006_taxonomy",
        path,
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_market_algebra_lane_routes_to_algebra_without_keyword_fallback():
    router = load_router()
    candidate = {
        "candidate_id": "MARKET-ALGEBRA-TAXONOMY-TEST",
        "lane": "market_algebra",
        "phase": "DISCOVERED",
        "queue_status": "NEEDS_DIRECTOR",
        "hypothesis": "Compare two representations.",
        "mechanism": "Mechanism text intentionally contains no routing keywords.",
        "needed_data": [],
        "required_tests": [],
    }

    routes = router.route_candidate(candidate)
    by_capability = {item["capability"]: item for item in routes}

    assert by_capability["algebra"] == {
        "candidate_id": "MARKET-ALGEBRA-TAXONOMY-TEST",
        "capability": "algebra",
        "reasons": ["lane=MARKET_ALGEBRA"],
    }
    assert by_capability["prebuild_killer"] == {
        "candidate_id": "MARKET-ALGEBRA-TAXONOMY-TEST",
        "capability": "prebuild_killer",
        "reasons": ["E007 cheap pre-build falsification required"],
    }
    assert set(by_capability) == {"algebra", "prebuild_killer"}
