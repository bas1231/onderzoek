from pathlib import Path
import importlib.util
import json
import tempfile

def load(path):
    spec=importlib.util.spec_from_file_location("recon_engine", path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def test_discover_routes_mechanism_and_behavior():
    m=load(Path("control/hourly/recon_engine.py"))
    routing={"scout":{"evidence":[{"source_id":"x","document_sha256":"abc","retrieved_at":"2026-01-01T00:00:00Z","snippet":"A failed market maker suffered adverse selection after a settlement rule change and longshot bias."}]}}
    f=m.discover(routing)
    modes={x["attack_mode"] for x in f}
    assert "PREDATOR" in modes
    assert "MECHANISM_BREAKER" in modes
    assert "HUMAN_WEAKNESS" in modes
    assert all(x["status"]=="WATCH" for x in f)
    assert all(x["economic_model"]["net_after_friction"] is None for x in f)

def test_no_signal_means_no_fabricated_finding():
    m=load(Path("control/hourly/recon_engine.py"))
    assert m.discover({"scout":{"evidence":[{"source_id":"x","snippet":"ordinary unrelated text"}]}})==[]
