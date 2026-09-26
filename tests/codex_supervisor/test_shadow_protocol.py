import json,pathlib,sys
import pytest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'control/codex_supervisor'))
import shadow_protocol as s
P=pathlib.Path
PROTOCOL=P(__file__).resolve().parents[2]/'knowledge/candidates/protocols/MANUAL-SCOUT-HENGELTJES-20260924-shadow-v1.json'
def load():return json.loads(PROTOCOL.read_text())
def test_real_protocol_identity_and_gates():
    p=load();assert s.validate_protocol({'candidate_id':p['candidate_id']},p)

def test_false_positive_fill_cancellation_touch_ambiguity_and_partial():
    assert s.conservative_fill(5,0,10)['quantity']==0
    assert s.conservative_fill(0,5)['quantity']==5
    assert s.conservative_fill(5,7)['quantity']==2
    assert s.conservative_fill(0,7,ambiguous=True)['status']=='UNPROVEN_FILL'

def test_no_hindsight_and_frozen_grid():
    with pytest.raises(ValueError):s.preclose_order('2026-09-26T10:00:00+00:00','2026-09-26T10:06:00+00:00','2026-09-26T10:05:00+00:00',{'maker_bid_cents':89})
    with pytest.raises(ValueError):s.preclose_order('2026-09-26T10:00:00+00:00','2026-09-26T10:01:00+00:00','2026-09-26T10:05:00+00:00',{'maker_bid_cents':89,'future_settlement':1})

def test_unsafe_protocol_fails_closed():
    p=load();p['safety']['paid_actions']=True
    with pytest.raises(ValueError):s.validate_protocol({'candidate_id':p['candidate_id']},p)

def test_miami_is_only_historical_fixture():
    p=load();r=s.run_deathchecks({'candidate_id':p['candidate_id']},p,{'protocol':'hash'},'local-test-commit')
    assert r['miami_regression_fixture']=={'fixture_only':True,'cost':'4.45','payout':'5.00','profit':'0.55','roi_pct':r['miami_regression_fixture']['roi_pct'],'pass':True}
    assert r['prospective_evidence'] is False and r['activation_authorized'] is False

def test_runner_has_no_execution_or_network_capability():
    import ast
    tree=ast.parse(P(s.__file__).read_text())
    imports={alias.name for node in ast.walk(tree) if isinstance(node,(ast.Import,ast.ImportFrom)) for alias in node.names}
    assert not imports.intersection({'urllib','http','socket','subprocess'})
    calls=[node.func.attr for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)]
    assert not set(calls).intersection({'connect','request','urlopen','execute_order','create_order'})

def test_all_three_deathchecks_explicit():
    r=s.run_deathchecks({'candidate_id':load()['candidate_id']},load(),{'protocol':'sha256'},'commit')
    assert [x['id'] for x in r['deathchecks']]==sorted(s.EXPECTED)
    assert r['all_deathchecks_pass']
