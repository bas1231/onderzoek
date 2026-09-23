from pathlib import Path
import importlib.util
import sys


def load():
    path = Path("control/hourly/market_instance_scanner.py")
    spec = importlib.util.spec_from_file_location("market_instance_scanner", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def market(ticker, event, *, strike_type=None, floor=None, cap=None,
           yes_ask=60, no_ask=45, rules="rules", secondary="secondary",
           expiration="2026-10-01T00:00:00Z", series="S", custom=None):
    return {
        "ticker": ticker,
        "event_ticker": event,
        "series_ticker": series,
        "market_type": "binary",
        "strike_type": strike_type,
        "floor_strike": floor,
        "cap_strike": cap,
        "custom_strike": custom,
        "expiration_time": expiration,
        "rules_primary": rules,
        "rules_secondary": secondary,
        "yes_ask": yes_ask,
        "no_ask": no_ask,
        "status": "open",
    }


def scan(m, snapshot, tmp_path):
    return m.scan_snapshot(snapshot, state_path=tmp_path / "state.json")


def test_same_market_complement_detects_only_gross_before_fees(tmp_path):
    m = load()
    snapshot = {
        "retrieved_at": "2026-09-23T15:00:00Z",
        "base_url": "test",
        "coverage": {"complete_open_universe": True},
        "events": [],
        "markets": [market("A", "E", yes_ask=40, no_ask=55)],
    }
    result = scan(m, snapshot, tmp_path)
    complement = [x for x in result["findings"] if x["relation_type"] == "COMPLEMENT"][0]
    screen = complement["economic_screens"][0]
    assert screen["status"] == "GROSS_POSITIVE_PENDING_FEES_DEPTH"
    assert screen["gross_margin_cents"] == "5"
    assert screen["net_ev_cents"] is None
    assert complement["net_positive_ev_proven"] is False
    assert result["economic_conclusion"] == "NO_PROVEN_EDGE"


def test_greater_threshold_dominance_uses_correct_basket(tmp_path):
    m = load()
    snapshot = {
        "retrieved_at": "2026-09-23T15:00:00Z",
        "base_url": "test",
        "events": [{"event_ticker": "E", "series_ticker": "S"}],
        "markets": [
            market("LOW", "E", strike_type="greater", floor=10, yes_ask=30, no_ask=75, rules="gt 10"),
            market("HIGH", "E", strike_type="greater", floor=20, yes_ask=20, no_ask=60, rules="gt 20"),
        ],
    }
    result = scan(m, snapshot, tmp_path)
    rel = [x for x in result["findings"] if x["relation_type"] == "NESTED_DOMINANCE"][0]
    assert rel["metadata"]["dominator"] == "LOW"
    assert rel["metadata"]["dominated"] == "HIGH"
    legs = rel["economic_screens"][0]["legs"]
    assert [(x["ticker"], x["side"]) for x in legs] == [("LOW", "YES"), ("HIGH", "NO")]
    assert rel["economic_screens"][0]["gross_margin_cents"] == "10"


def test_less_threshold_dominance_reverses_direction(tmp_path):
    m = load()
    snapshot = {
        "retrieved_at": "2026-09-23T15:00:00Z",
        "base_url": "test",
        "events": [{"event_ticker": "E"}],
        "markets": [
            market("LOWCAP", "E", strike_type="less", cap=10, yes_ask=20, no_ask=80, rules="lt 10"),
            market("HIGHCAP", "E", strike_type="less", cap=20, yes_ask=35, no_ask=55, rules="lt 20"),
        ],
    }
    result = scan(m, snapshot, tmp_path)
    rel = [x for x in result["findings"] if x["relation_type"] == "NESTED_DOMINANCE"][0]
    assert rel["metadata"]["dominator"] == "HIGHCAP"
    assert rel["metadata"]["dominated"] == "LOWCAP"


def test_declared_mutually_exclusive_event_screens_all_no_floor(tmp_path):
    m = load()
    snapshot = {
        "retrieved_at": "2026-09-23T15:00:00Z",
        "base_url": "test",
        "events": [{"event_ticker": "E", "mutually_exclusive": True}],
        "markets": [
            market("A", "E", no_ask=30, rules="A"),
            market("B", "E", no_ask=30, rules="B"),
            market("C", "E", no_ask=30, rules="C"),
        ],
    }
    result = scan(m, snapshot, tmp_path)
    rel = [x for x in result["findings"] if x["relation_type"] == "MUTUALLY_EXCLUSIVE_SET"][0]
    screen = rel["economic_screens"][0]
    assert screen["guaranteed_payout_cents"] == "200"
    assert screen["gross_cost_cents"] == "90"
    assert screen["gross_margin_cents"] == "110"
    assert rel["net_positive_ev_proven"] is False


def test_disjoint_ranges_generate_mutual_exclusion_candidate(tmp_path):
    m = load()
    snapshot = {
        "retrieved_at": "2026-09-23T15:00:00Z",
        "base_url": "test",
        "events": [{"event_ticker": "E"}],
        "markets": [
            market("R1", "E", strike_type="between", floor=0, cap=10, rules="0-10"),
            market("R2", "E", strike_type="between", floor=11, cap=20, rules="11-20"),
        ],
    }
    result = scan(m, snapshot, tmp_path)
    rels = [x for x in result["findings"] if x["relation_type"] == "MUTUALLY_EXCLUSIVE_PAIR"]
    assert len(rels) == 1
    assert rels[0]["metadata"]["basis"] == "disjoint_between_ranges"


def test_exact_semantics_can_cross_series_but_stays_unproven_edge(tmp_path):
    m = load()
    a = market("A", "E1", strike_type="greater", floor=10, rules="identical", series="S1")
    b = market("B", "E2", strike_type="greater", floor=10, rules="identical", series="S2")
    snapshot = {
        "retrieved_at": "2026-09-23T15:00:00Z",
        "base_url": "test",
        "events": [],
        "markets": [a, b],
    }
    result = scan(m, snapshot, tmp_path)
    rel = [x for x in result["findings"] if x["relation_type"] == "DECLARED_EQUIVALENCE"][0]
    assert rel["metadata"]["cross_series"] is True
    assert rel["semantic_proof"]["status"] == "EXACT_DECLARED_SEMANTICS_MATCH"
    assert rel["net_positive_ev_proven"] is False


def test_same_title_different_rules_does_not_create_equivalence(tmp_path):
    m = load()
    a = market("A", "E1", rules="window starts Monday", series="S1")
    b = market("B", "E2", rules="window starts Tuesday", series="S2")
    a["title"] = b["title"] = "Same title"
    snapshot = {
        "retrieved_at": "2026-09-23T15:00:00Z",
        "base_url": "test",
        "events": [],
        "markets": [a, b],
    }
    result = scan(m, snapshot, tmp_path)
    assert not [x for x in result["findings"] if x["relation_type"] == "DECLARED_EQUIVALENCE"]


def test_routing_evidence_never_claims_net_positive_ev(tmp_path):
    m = load()
    snapshot = {
        "retrieved_at": "2026-09-23T15:00:00Z",
        "base_url": "test",
        "events": [],
        "markets": [market("A", "E", yes_ask=40, no_ask=55)],
    }
    result = scan(m, snapshot, tmp_path)
    routed = m.routing_evidence(result)
    assert "microstructure" in routed
    assert all("net_positive_ev_proven=false" in item["snippet"] for item in routed["microstructure"])


def test_semantic_change_detection_ignores_price_only_changes(tmp_path):
    m = load()
    state = tmp_path / "state.json"
    base = {
        "retrieved_at": "2026-09-23T15:00:00Z",
        "base_url": "test",
        "events": [],
        "markets": [market("A", "E", yes_ask=40, no_ask=55)],
    }
    first = m.scan_snapshot(base, state_path=state)
    changed_price = {
        **base,
        "retrieved_at": "2026-09-23T16:00:00Z",
        "markets": [market("A", "E", yes_ask=45, no_ask=50)],
    }
    second = m.scan_snapshot(changed_price, state_path=state)
    assert first["change_detection"]["new_market_count"] == 1
    assert second["change_detection"]["semantic_change_count"] == 0
    assert second["change_detection"]["new_market_count"] == 0
