from pathlib import Path
import importlib.util
import tempfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("candidate_store_testmod", ROOT / "control/edge_hunter/candidate_store.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def make(cid):
    return mod.create(cid,"weather","h","m",["d"],["p"],"metric","market","exec")

def test_fail_closed_promotion():
    old = mod.CANDIDATE_DIR
    with tempfile.TemporaryDirectory() as td:
        mod.CANDIDATE_DIR = Path(td)
        make("TEST-CANDIDATE")
        try:
            mod.promote("TEST-CANDIDATE","MECHANISM_DEFINED")
            assert False
        except ValueError:
            pass
        mod.gate("TEST-CANDIDATE","mechanism","PASS","evidence:test")
        mod.promote("TEST-CANDIDATE","MECHANISM_DEFINED")
        assert mod.load("TEST-CANDIDATE")["phase"] == "MECHANISM_DEFINED"
    mod.CANDIDATE_DIR = old

def test_failed_gate_rejects():
    old = mod.CANDIDATE_DIR
    with tempfile.TemporaryDirectory() as td:
        mod.CANDIDATE_DIR = Path(td)
        make("TEST-FAIL")
        mod.gate("TEST-FAIL","mechanism","FAIL","evidence:negative")
        assert mod.load("TEST-FAIL")["decision"] == "REJECTED"
    mod.CANDIDATE_DIR = old
