"""Gedragstests voor de audit; alle data synthetisch, geen live services."""
import contextlib
import datetime as dt
from decimal import Decimal
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import runpy
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'control'))
sys.path.insert(0, str(ROOT / 'control/weather'))


def load(name, path):
    spec = importlib.util.spec_from_file_location('audit_' + name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def router(tmp_path):
    m = load('router', 'control/tampermonkey_multichat/command_router.py')
    m.ROUTES = tmp_path
    return m


@pytest.mark.parametrize('raw', ['{', '[]', 'null', '{}', '{"task_id":"wrong","chat_id":"chat-old"}'])
def test_corrupt_existing_route_fails_closed(router, raw):
    p = router.ROUTES / 'TASK-A.json'
    p.write_text(raw)
    with pytest.raises(ValueError):
        router.write_route('TASK-A', 'chat-new', 'consumer-new')
    assert p.read_text() == raw


def test_route_retry_idempotent_and_cross_consumer_rejected(router):
    first = router.write_route('TASK-A', 'chat-same', 'consumer-a')
    p = router.ROUTES / 'TASK-A.json'
    original = p.read_bytes()
    assert router.write_route('TASK-A', 'chat-same', 'consumer-a') == first
    assert p.read_bytes() == original
    with pytest.raises(ValueError):
        router.write_route('TASK-A', 'chat-same', 'consumer-b')
    with pytest.raises(ValueError):
        router.write_route('TASK-A', 'chat-other', 'consumer-a')


@pytest.mark.parametrize('body,declared,status', [(b'[]',2,400),(b'null',4,400),(b'"hi"',4,400),(b'{',1,400),(b'{}',9,400),(b'{}',-1,400),(b'{}',32769,413)])
def test_bad_envelope_is_visible_and_never_forwarded(router, monkeypatch, body, declared, status):
    h = object.__new__(router.Handler)
    h.path = '/command'
    h.authorized = lambda: True
    h.headers = {'Content-Length': str(declared)}
    h.rfile = io.BytesIO(body)
    replies = []
    h.reply = lambda code, payload: replies.append((code, payload))
    monkeypatch.setattr(router, 'forward_command', lambda *a: pytest.fail('forward must not occur'))
    h.do_POST()
    assert replies[0][0] == status
    assert not list(router.ROUTES.iterdir())


def test_malformed_upstream_success_is_not_success(router, monkeypatch):
    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self, *a): return b'{"ok":'
    monkeypatch.setattr(router, 'urlopen', lambda *a, **k: Response())
    status, result = router.forward_command({'action':'BRIDGE_PING','task_id':'TASK-A'}, 'synthetic-only')
    assert status == 502
    assert result['ok'] is False


def proof_result(m):
    return {'candidate_id':'SYNTHETIC', 'status':'PASS', 'gates':{x:'PASS' for x in m.PROOF_GATES}, 'economics':{'fees':0.01,'spread':0.01,'slippage':0.01,'fills':'validated','settlement':'validated','capacity':'bounded','net_edge':0.02}}


@pytest.mark.parametrize('key,value', [('net_edge',-1),('net_edge',0),('net_edge',True),('net_edge','0.1'),('net_edge',float('nan')),('net_edge',float('inf')),('fees',None),('fees',True),('fees',-1),('fees',float('inf')),('slippage','unknown'),('fills',None),('settlement',{})])
def test_proof_rejects_invalid_economics(key, value):
    m=load('orchestrator','control/hourly/agent_orchestrator.py')
    result=proof_result(m);result['economics'][key]=value
    accepted,reasons=m.proof_gate(result,{'SYNTHETIC'})
    assert not accepted and reasons


def test_proof_valid_candidate_still_accepted_but_requires_upstream():
    m=load('orchestrator','control/hourly/agent_orchestrator.py');row=proof_result(m)
    assert m.proof_gate(row,{'SYNTHETIC'}) == (True, [])
    assert m.proof_gate(row,set())[0] is False


def test_actual_timeout_preserves_logs_and_terminal_state(tmp_path, monkeypatch):
    m=load('executor','control/executor.py')
    for name in ['PENDING','RUNNING','COMPLETED','FAILED','RESULTS']:
        d=tmp_path/name;d.mkdir();monkeypatch.setattr(m,name,d)
    monkeypatch.setattr(m,'ROOT',tmp_path)
    task=SimpleNamespace(task_id='SYNTHETIC', hypothesis_id='SYNTHETIC', task_class='infrastructure', working_directory='.', timeout_seconds=.1, command=[sys.executable,'-c','import os,time; os.write(1,b"partial-out\\xff"); os.write(2,b"partial-err\\xff"); time.sleep(2)'])
    monkeypatch.setattr(m,'Task',SimpleNamespace(model_validate=lambda _:task))
    monkeypatch.setattr(m,'task_provenance_in_head',lambda *a:{'ok':True})
    monkeypatch.setattr(m,'support_script_in_head',lambda *a:{'ok':True})
    monkeypatch.setattr(m,'current_commit',lambda:'0'*40)
    monkeypatch.setattr(m,'lifecycle_load',lambda *a:{'state':'ACCEPTED'})
    states=[];monkeypatch.setattr(m,'lifecycle_update',lambda *a:states.append(a))
    monkeypatch.setattr(m,'WORK_CADENCE',SimpleNamespace(check=lambda **k:{'allowed':True}))
    monkeypatch.setattr(m,'check_action',lambda *a:{'status':'ALLOWED','reason':'fixture'})
    monkeypatch.setattr(m,'git',lambda *a,**k:SimpleNamespace(returncode=0))
    p=m.PENDING/'SYNTHETIC.json';p.write_text('{}')
    assert m.process_task(p)=='failed'
    result=json.loads((m.RESULTS/'SYNTHETIC/RESULT.json').read_text())
    assert result['exit_code']==124 and result['status']=='failed'
    assert states[-1][1]=='FAILED'
    assert not (m.RUNNING/p.name).exists() and (m.FAILED/p.name).exists()
    for stream in ['stdout','stderr']:
        log=m.RESULTS/'SYNTHETIC'/(stream+'.log')
        assert result[stream+'_sha256']==hashlib.sha256(log.read_bytes()).hexdigest()
        assert 'partial-' in log.read_text()
    assert 'TASK TIMEOUT' in (m.RESULTS/'SYNTHETIC/stderr.log').read_text()


def manifest(stamp='2026-09-25T00:00:00+00:00', config='v1'):
    return {'timestamp_semantics':'response_body_received','retrieved_at':stamp,'cities':[{'city':'nyc','config_version':config,'retrieved_at':stamp,'latest_complete':{'t':100,'v':79,'contributors':1},'latest_incomplete':{'t':101,'stations':[{'temp_f':80}]}}]}


def test_receipt_provenance_and_city_clock():
    m=load('reaction','control/weather/market_reaction.py');row=manifest()
    row['cities'][0]['retrieved_at']='2026-09-25T00:00:05+00:00'
    event=m.extract_kwi_events([row],'nyc')[0]
    assert event['available_at_ms']==m.parse_ts_ms('2026-09-25T00:00:05+00:00')
    del row['timestamp_semantics']
    assert m.extract_kwi_events([row],'nyc')==[]


@pytest.mark.parametrize('mode', ['later','earlier','same_time','different_config','unknown_clock'])
def test_target_must_be_later_same_config(tmp_path, monkeypatch, mode):
    home=tmp_path/'home';root=tmp_path/'root';root.mkdir()
    folder=home/'.local/state/prediction-research/kalshi_weather_index_manifests';folder.mkdir(parents=True)
    prot=root/'knowledge/candidates/protocols';prot.mkdir(parents=True)
    (prot/'KWI-FULL-STATION-PRECANONICAL-24H-V1.json').write_text(json.dumps({'prospective_cutoff':'2026-09-25T00:00:00+00:00','window_end':'2026-09-26T00:00:00+00:00','minimum_eligible_pairs_per_city':30,'minimum_eligible_cities':2}))
    signal=manifest('2026-09-25T00:00:10+00:00')
    second={'later':20,'earlier':5,'same_time':10,'different_config':20,'unknown_clock':20}[mode]
    target=manifest(f'2026-09-25T00:00:{second:02d}+00:00','v2' if mode=='different_config' else 'v1')
    target['cities'][0]['latest_complete']={'t':101,'v':80,'contributors':1}
    target['cities'][0].pop('latest_incomplete')
    if mode=='unknown_clock':
        signal.pop('timestamp_semantics');target.pop('timestamp_semantics')
    for i,row in enumerate([signal,target]):(folder/f'{i}.json').write_text(json.dumps(row))
    monkeypatch.chdir(root);monkeypatch.setattr(Path,'home',lambda:home)
    with contextlib.redirect_stdout(io.StringIO()):values=runpy.run_path(str(ROOT/'control/jobs/evaluate_kwi_full_station_checkpoint_e369.py'))
    assert len(values['eligible']) == (1 if mode=='later' else 0)


def test_continuous_quiet_book_and_missing_coverage():
    m=load('reaction','control/weather/market_reaction.py');D=Decimal
    state=m.MarketState(ticker='SYNTHETIC',ts_ms=1000,yes_bid=D('.4'),yes_ask=D('.6'),no_bid=D('.4'),no_ask=D('.6'),yes_bid_qty=D(1),no_bid_qty=D(1),transport='ws')
    event={'available_at_ms':10000}
    assert m.analyze_reaction(event,[state],coverage_ms=list(range(9000,41000,1000)))['status']==m.NO_REACTION_OBSERVED_WITHIN_WINDOW
    assert m.analyze_reaction(event,[state],coverage_ms=[9500,100000])['status']==m.UNPROVEN_REACTION


@pytest.mark.parametrize('scenario', ['draft','no_button','concurrent_edit','normal'])
def test_composer_ownership_and_retry(scenario):
    js=r'''
const fs=require('fs');
const src=fs.readFileSync('control/tampermonkey_multichat/prediction-chat-wake.user.js','utf8');
const fn=src.slice(src.indexOf('  async function submitMessage('),src.indexOf('  async function ack('));
const scenario=process.argv[1];
let composer={value:scenario==='draft'?'USER DRAFT':''}, sent=[], polls=0;
const document={querySelectorAll:()=>sent.map(text=>({textContent:text}))};
const chatIsBusy=()=>false,findComposer=()=>composer,status=()=>{};
const setComposerText=(el,text)=>el.value=text;
const sleep=async()=>{if(scenario==='concurrent_edit')composer.value='NEW USER TEXT';};
const findSendButton=()=>{polls++;if(scenario==='no_button'||(scenario==='concurrent_edit'&&polls===1))return null;return {click:()=>{sent.push(composer.value);composer.value='';}};};
eval(fn+';submitMessage("BRIDGE").then(ok=>console.log(JSON.stringify({ok,sent,remaining:composer.value})))');
'''
    row=json.loads(subprocess.check_output(['node','-e',js,scenario],cwd=ROOT,text=True))
    if scenario=='normal':assert row=={'ok':True,'sent':['BRIDGE'],'remaining':''}
    elif scenario=='draft':assert row=={'ok':False,'sent':[],'remaining':'USER DRAFT'}
    elif scenario=='concurrent_edit':assert row=={'ok':False,'sent':[],'remaining':'NEW USER TEXT'}
    else:assert row=={'ok':False,'sent':[],'remaining':''}


@pytest.mark.parametrize('action', ['place-order','withdraw_wallet','send_crypto','purchase_api_credits','paid_api_payment'])
def test_restored_policy_still_blocks_financial_actions(action):
    m=load('policy','control/policy_check.py')
    assert m.check_action(action)['status']=='BLOCKED_BY_POLICY'


@pytest.mark.parametrize('raw', [None,'{','[]','{}','{"mode":"live"}'])
def test_policy_configuration_missing_or_invalid_fails_closed(tmp_path, raw):
    m=load('policy','control/policy_check.py');m.POLICY=tmp_path/'policy.json'
    if raw is not None:m.POLICY.write_text(raw)
    assert m.check_action('write_report')['status']=='BLOCKED_BY_POLICY'


def test_policy_safe_local_research_remains_allowed():
    m=load('policy','control/policy_check.py')
    assert m.check_action('write_report')['status']=='ALLOWED'


def test_policy_denial_terminalizes_queue(tmp_path, monkeypatch):
    m=load('executor','control/executor.py')
    for name in ['PENDING','RUNNING','COMPLETED','FAILED','RESULTS']:
        d=tmp_path/name;d.mkdir();monkeypatch.setattr(m,name,d)
    monkeypatch.setattr(m,'ROOT',tmp_path)
    task=SimpleNamespace(task_id='SYNTHETIC',hypothesis_id='SYNTHETIC',task_class='infrastructure',working_directory='.',timeout_seconds=1,command=['synthetic'])
    monkeypatch.setattr(m,'Task',SimpleNamespace(model_validate=lambda _:task))
    monkeypatch.setattr(m,'task_provenance_in_head',lambda *a:{'ok':True})
    monkeypatch.setattr(m,'support_script_in_head',lambda *a:{'ok':True})
    monkeypatch.setattr(m,'current_commit',lambda:'0'*40)
    monkeypatch.setattr(m,'lifecycle_load',lambda *a:{'state':'ACCEPTED'})
    states=[];monkeypatch.setattr(m,'lifecycle_update',lambda *a:states.append(a))
    monkeypatch.setattr(m,'WORK_CADENCE',SimpleNamespace(check=lambda **k:{'allowed':True}))
    monkeypatch.setattr(m,'check_action',lambda *a:{'status':'BLOCKED_BY_POLICY','reason':'fixture denial'})
    monkeypatch.setattr(m,'git',lambda *a,**k:SimpleNamespace(returncode=0))
    p=m.PENDING/'SYNTHETIC.json';p.write_text('{}')
    assert m.process_task(p)=='blocked'
    assert not (m.RUNNING/p.name).exists()
    assert (m.FAILED/p.name).exists()
    assert states[-1][1]=='BLOCKED_BY_POLICY'
    assert json.loads((m.RESULTS/'SYNTHETIC/RESULT.json').read_text())['status']=='BLOCKED_BY_POLICY'


def test_composer_clear_alone_is_not_delivery_evidence():
    js=r'''
const fs=require('fs');
const src=fs.readFileSync('control/tampermonkey_multichat/prediction-chat-wake.user.js','utf8');
const fn=src.slice(src.indexOf('  async function submitMessage('),src.indexOf('  async function ack('));
let composer={value:''};
const document={querySelectorAll:()=>[]};
const chatIsBusy=()=>false,findComposer=()=>composer,status=()=>{};
const setComposerText=(el,text)=>el.value=text,sleep=async()=>{};
const findSendButton=()=>({click:()=>{composer.value='';}});
eval(fn+';submitMessage("SYNTHETIC DELIVERY").then(ok=>console.log(JSON.stringify({ok})))');
'''
    result=json.loads(subprocess.check_output(['node','-e',js],cwd=ROOT,text=True))
    assert result['ok'] is False


@pytest.mark.parametrize('mode',['foreign_ticker','nonfinite_price'])
def test_invalid_post_event_state_cannot_prove_reaction(mode):
    m=load('reaction','control/weather/market_reaction.py');D=Decimal
    pre=m.MarketState('X',9000,D('.4'),D('.6'),D('.4'),D('.6'),D(10),D(10),'rest')
    post=m.MarketState('Y' if mode=='foreign_ticker' else 'X',11000,D('.5') if mode=='foreign_ticker' else D('Infinity'),D('.6'),D('.4'),D('.5'),D(10),D(10),'rest')
    result=m.analyze_reaction({'available_at_ms':10000},[pre,post],window_ms=1000)
    assert result['status']==m.UNPROVEN_REACTION
