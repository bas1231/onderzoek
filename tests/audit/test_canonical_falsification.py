"""Nieuwe canonical counterexamples; geen services, orders of credentials."""
import ast
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from test_reliability_regressions import load

ROOT=Path(__file__).resolve().parents[2]

@pytest.mark.parametrize('exc',[TimeoutError('synthetic'),OSError('synthetic')])
def test_upstream_transport_error_is_explicit_failure(tmp_path,monkeypatch,exc):
    m=load('router_final','control/tampermonkey_multichat/command_router.py')
    def fail(*a,**k):raise exc
    monkeypatch.setattr(m,'urlopen',fail)
    code,body=m.forward_command({'action':'BRIDGE_PING','task_id':'SYNTHETIC'},'synthetic')
    assert code==503 and body['ok'] is False

@pytest.mark.parametrize('raw',[b'null',b'[]',b'{"ok":false}',b'{"ok":1}',b'{"ok":true}'])
def test_upstream_success_requires_boolean_confirmation(monkeypatch,raw):
    m=load('router_final','control/tampermonkey_multichat/command_router.py')
    class Response:
        status=200
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def read(self,*a):return raw
    monkeypatch.setattr(m,'urlopen',lambda *a,**k:Response())
    code,body=m.forward_command({'action':'BRIDGE_PING','task_id':'SYNTHETIC'},'synthetic')
    assert code==(200 if raw==b'{"ok":true}' else 502)


def test_repeated_ack_handler_persists_without_socket(tmp_path):
    m=load('bridge_final','control/tampermonkey_multichat/bridge_server_v2.py')
    m.DATA_DIR=tmp_path;m.OUTBOX=tmp_path/'outbox';m.SENT=tmp_path/'sent';m.ROUTES=tmp_path/'routes';m.DEFAULT_CHAT_FILE=tmp_path/'default.json'
    m.ensure_dirs();m.LEASES.clear()
    event={'version':1,'event_id':'1234567890-deadbeef','task_id':'SYNTHETIC','message':'RESULT_READY: SYNTHETIC'}
    (m.ROUTES/'SYNTHETIC.json').write_text(json.dumps({'task_id':'SYNTHETIC','chat_id':'chat-test'}))
    (m.OUTBOX/(event['event_id']+'.json')).write_text(json.dumps(event))
    assert m.oldest_event('chat-test','tab-test')[0]
    body=json.dumps({'event_id':event['event_id'],'chat_id':'chat-test','consumer_id':'tab-test'}).encode()
    responses=[]
    for _ in range(2):
        h=object.__new__(m.Handler);h.path='/ack';h.headers={'Authorization':'Bearer synthetic','Content-Length':str(len(body))};h.server=SimpleNamespace(bridge_token='synthetic');h.rfile=io.BytesIO(body)
        h.reply_json=lambda code,payload:responses.append((code,payload))
        h.do_POST()
    assert all(code==200 and b['ok'] for code,b in responses)
    assert responses[1][1]['already_acked']
    assert not list(m.OUTBOX.iterdir()) and (m.SENT/(event['event_id']+'.json')).exists()
    assert m.oldest_event('chat-test','tab-test')==(None,None)


def test_owner_installer_preserves_idle_policy_and_nonce():
    m=load('installer_final','control/tampermonkey_multichat/install_hardened_bridge.py')
    original=(ROOT/'control/tampermonkey_multichat/bridge_server_hardened.py').read_text()
    patched=m.hardened_runtime_source(original)
    assert m.hardened_runtime_source(patched)==patched
    tree=ast.parse(patched)
    constant=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DEFAULT_HEARTBEAT_INTERVAL' for t in n.targets))
    assert ast.literal_eval(constant.value)==m.HEARTBEAT_IDLE_SECONDS==600
    fun=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='heartbeat_message')
    ns={};exec(compile(ast.Module(body=[fun],type_ignores=[]),'synthetic','exec'),ns)
    assert ns['heartbeat_message']('nonce-A')!=ns['heartbeat_message']('nonce-B')
    assert 'NIEUWE' in ns['heartbeat_message']('nonce-A')
    assert '"heartbeat_retry_nonce": True' in patched and '"heartbeat_fresh_task_id_required": True' in patched

@pytest.mark.parametrize('key',['net_edge','fees'])
def test_huge_json_integer_does_not_crash_proof_gate(key):
    from test_reliability_regressions import proof_result
    m=load('proof_final','control/hourly/agent_orchestrator.py');row=proof_result(m)
    row['economics'][key]=10**400
    accepted,reasons=m.proof_gate(row,{'SYNTHETIC'})
    assert not accepted and reasons


def test_earliest_city_receipt_overrules_manifest_batch_order(tmp_path,monkeypatch):
    import contextlib,runpy
    from test_reliability_regressions import manifest
    home=tmp_path/'home';root=tmp_path/'root';root.mkdir()
    folder=home/'.local/state/prediction-research/kalshi_weather_index_manifests';folder.mkdir(parents=True)
    prot=root/'knowledge/candidates/protocols';prot.mkdir(parents=True)
    (prot/'KWI-FULL-STATION-PRECANONICAL-24H-V1.json').write_text(json.dumps({'prospective_cutoff':'2026-09-25T00:00:00+00:00','window_end':'2026-09-26T00:00:00+00:00','minimum_eligible_pairs_per_city':30,'minimum_eligible_cities':2}))
    signal=manifest('2026-09-25T00:00:10+00:00');late=manifest('2026-09-25T00:00:20+00:00');early=manifest('2026-09-25T00:00:30+00:00')
    early['cities'][0]['retrieved_at']='2026-09-25T00:00:05+00:00'
    for target in [late,early]:
        target['cities'][0]['latest_complete']={'t':101,'v':80,'contributors':1};target['cities'][0].pop('latest_incomplete')
    for i,row in enumerate([signal,late,early]):(folder/f'{i}.json').write_text(json.dumps(row))
    monkeypatch.chdir(root);monkeypatch.setattr(Path,'home',lambda:home)
    with contextlib.redirect_stdout(io.StringIO()):out=runpy.run_path(str(ROOT/'control/jobs/evaluate_kwi_full_station_checkpoint_e369.py'))
    assert out['eligible']==[]
