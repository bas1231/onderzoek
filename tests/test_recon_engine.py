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


def test_hunt_gate_requires_repeated_independent_public_sources(tmp_path):
    m=load(Path("control/hourly/recon_engine.py"))
    m.WATCHLIST=tmp_path/"watchlist.json"
    m.GRAPH=tmp_path/"graph.json"
    first=m.discover({"scout":{"evidence":[{"source_id":"rules-a","document_sha256":"a","retrieved_at":"2026-01-01T00:00:00Z","snippet":"Prediction market contracts settle from an official settlement source. Traders price each contract and payout using the named source."}]}})
    target=[x for x in first if x["attack_mode"]=="MECHANISM_BREAKER"][0]
    m.update_watchlist([target])
    stored=m.load_json(m.WATCHLIST,{})["items"][0]
    assert stored["status"]=="WATCH"
    assert stored["hunt_gate"]["passes"] is False

    second=dict(target)
    second["observed_at"]="2026-01-02T00:00:00Z"
    second["sources"]=[dict(target["sources"][0], source_id="rules-b", document_sha256="b")]
    m.update_watchlist([second])
    stored=m.load_json(m.WATCHLIST,{})["items"][0]
    assert stored["status"]=="HUNT"
    assert stored["hunt_gate"]["passes"] is True
    assert stored["independent_source_count"]==2
    assert "RECON_HUNT" in stored["labels"]

def test_same_source_repetition_does_not_promote_to_hunt(tmp_path):
    m=load(Path("control/hourly/recon_engine.py"))
    m.WATCHLIST=tmp_path/"watchlist.json"
    m.GRAPH=tmp_path/"graph.json"
    finding=m.discover({"scout":{"evidence":[{"source_id":"rules-a","document_sha256":"a","retrieved_at":"2026-01-01T00:00:00Z","snippet":"Prediction market contracts settle from an official settlement source. Traders price each contract and payout using the named source."}]}})[0]
    m.update_watchlist([finding])
    repeat=dict(finding)
    repeat["sources"]=[dict(finding["sources"][0], document_sha256="b")]
    m.update_watchlist([repeat])
    stored=m.load_json(m.WATCHLIST,{})["items"][0]
    assert stored["status"]=="WATCH"
    assert stored["independent_source_count"]==1


def test_hunt_plan_is_research_only_and_falsification_first(tmp_path):
    m=load(Path("control/hourly/recon_engine.py"))
    m.HUNT_PLANS=tmp_path/"hunts"
    item={
        "id":"RECON-test","status":"HUNT","attack_mode":"PREDATOR",
        "claim":"Repeated public evidence suggests a mechanism; unproven.",
        "observation_count":2,
        "observation_history":[
            {"source_id":"a","document_sha256":"1"},
            {"source_id":"b","document_sha256":"2"},
        ],
        "economic_model":{"who_loses":None,"why":None,"who_captures":None,"public_trigger":"adverse selection"},
        "falsification":{"next_decisive_test":"Test point-in-time predictiveness after costs.","specialist_route":["microstructure","behavioral"]},
    }
    plans,path=m.write_hunt_plans("run-test",[item])
    assert path is not None and path.exists()
    assert len(plans)==1
    plan=plans[0]
    assert plan["tests"]["primary_falsification"]=="Test point-in-time predictiveness after costs."
    assert plan["evidence"]["independent_source_ids"]==["a","b"]
    assert plan["execution_gate"]["research_only"] is True
    assert plan["execution_gate"]["live_trading"] is False
    assert plan["execution_gate"]["paid_actions"] is False
    assert plan["execution_gate"]["wallet_actions"] is False
    assert plan["execution_gate"]["economic_conclusion"]=="NO_PROVEN_EDGE"

def test_no_hunt_means_no_hunt_plan_file(tmp_path):
    m=load(Path("control/hourly/recon_engine.py"))
    m.HUNT_PLANS=tmp_path/"hunts"
    plans,path=m.write_hunt_plans("run-test",[{"id":"x","status":"WATCH"}])
    assert plans==[]
    assert path is None
    assert not m.HUNT_PLANS.exists()
