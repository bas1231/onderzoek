from pathlib import Path
import importlib.util

def load(path):
    spec=importlib.util.spec_from_file_location("recon_engine", path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def test_discover_routes_mechanism_and_behavior():
    m=load(Path("control/hourly/recon_engine.py"))
    routing={"scout":{"evidence":[{"source_id":"x","document_sha256":"abc","retrieved_at":"2026-01-01T00:00:00Z","snippet":"A failed market maker suffered adverse selection after a settlement rule change and longshot bias."}]}}
    f=m.discover(routing)
    modes={x["attack_mode"] for x in f if x["status"]=="WATCH"}
    assert "PREDATOR" in modes
    assert "MECHANISM_BREAKER" in modes
    assert "HUMAN_WEAKNESS" in modes
    assert all(x["economic_model"]["net_after_friction"] is None for x in f)

def test_no_signal_means_no_fabricated_finding():
    m=load(Path("control/hourly/recon_engine.py"))
    assert m.discover({"scout":{"evidence":[{"source_id":"x","snippet":"ordinary unrelated text"}]}})==[]

def test_footer_loss_is_discovery_noise_not_watch():
    m=load(Path("control/hourly/recon_engine.py"))
    routing={"scout":{"evidence":[{"source_id":"cftc","document_sha256":"x","retrieved_at":"2026-01-01T00:00:00Z","snippet":"Privacy Policy Web Policy FOIA Accessibility Statement Submit Tips & Complaints Headquarters. Loss information."}]}}
    f=m.discover(routing)
    assert f
    assert all(x["status"]=="DISCOVER" for x in f)
    assert all("RECON_DISCOVERY_NOISE" in x["labels"] for x in f)

def test_generic_api_navigation_does_not_reach_watch():
    m=load(Path("control/hourly/recon_engine.py"))
    routing={"scout":{"evidence":[{"source_id":"docs","document_sha256":"y","retrieved_at":"2026-01-01T00:00:00Z","snippet":"API Reference Changelog Glossary Specifications Sign in Search Documentation."}]}}
    f=m.discover(routing)
    assert f
    assert all(x["status"]=="DISCOVER" for x in f)

def test_context_supported_settlement_signal_reaches_watch():
    m=load(Path("control/hourly/recon_engine.py"))
    routing={"scout":{"evidence":[{"source_id":"rules","document_sha256":"z","retrieved_at":"2026-01-01T00:00:00Z","snippet":"Weather prediction market contracts settle from an official settlement source. Traders price each contract and payout using the named source."}]}}
    f=m.discover(routing)
    settlement=[x for x in f if x["attack_mode"]=="MECHANISM_BREAKER"]
    assert settlement
    assert all(x["status"]=="WATCH" for x in settlement)
    assert settlement[0]["quality"]["economic_context_count"] >= 2


def test_legacy_watch_noise_is_demoted_from_persistent_state(tmp_path):
    m=load(Path("control/hourly/recon_engine.py"))
    m.WATCHLIST=tmp_path/"watchlist.json"
    m.GRAPH=tmp_path/"graph.json"
    noise=m.discover({"scout":{"evidence":[{"source_id":"cftc","document_sha256":"x","retrieved_at":"2026-01-01T00:00:00Z","snippet":"Privacy Policy Web Policy FOIA Accessibility Statement Submit Tips & Complaints Headquarters. Loss information."}]}})[0]
    legacy=dict(noise)
    legacy["status"]="WATCH"
    legacy["labels"]=["RECON_ANOMALY"]
    m.save_json(m.WATCHLIST, {"version":1,"items":[legacy]})
    m.save_json(m.GRAPH, {"version":1,"nodes":[{"id":legacy["id"],"type":"recon_finding","status":"WATCH"},{"id":"role:microstructure","type":"specialist"}],"edges":[{"from":legacy["id"],"to":"role:microstructure","type":"route_to"}]})
    watch=m.update_watchlist([noise])
    graph=m.update_graph([noise])
    persisted=m.load_json(m.WATCHLIST,{})
    persisted_graph=m.load_json(m.GRAPH,{})
    assert watch["demoted_noise"] == 1
    assert persisted["items"] == []
    assert all(x["id"] != legacy["id"] for x in persisted_graph["nodes"])
    assert all(x["from"] != legacy["id"] for x in persisted_graph["edges"])
