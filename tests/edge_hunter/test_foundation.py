from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]

def test_lane_registry_is_general():
    data = json.loads((ROOT / "control/edge_hunter/lane_registry.json").read_text())
    lanes = set(data["lanes"])
    assert "weather" in lanes
    assert "market_algebra" in lanes
    assert "microstructure" in lanes
    assert "settlement_rules" in lanes
    assert len(lanes) >= 8
    assert "Weather is one lane" in data["purpose"]

def test_candidate_schema_fail_closed():
    data = json.loads((ROOT / "control/edge_hunter/candidate_schema.json").read_text())
    gates = data["hard_gates"]
    assert gates["live_trading"] is False
    assert gates["paid_actions"] is False
    assert gates["wallet_actions"] is False
    assert gates["point_in_time_required"] is True
    assert gates["executable_market_price_required_for_market_edge"] is True
