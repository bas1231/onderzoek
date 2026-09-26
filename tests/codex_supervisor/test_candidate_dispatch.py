import json,pathlib,sys
import pytest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'control/codex_supervisor'))
import supervisor as m
import candidate_dispatch as d
ROOT=pathlib.Path(__file__).resolve().parents[2]
PROTOCOL=ROOT/'knowledge/candidates/protocols/MANUAL-SCOUT-HENGELTJES-20260924-shadow-v1.json'

def candidate(repo,cid='A',priority='P2',status='NEEDS_DIRECTOR',**extra):
    p=repo/'knowledge/candidates'/f'{cid}.json';p.parent.mkdir(parents=True,exist_ok=True)
    x=dict(candidate_id=cid,priority=priority,queue_status=status,created_at='2026-09-26T09:00:00+00:00',queue_entered_at='2026-09-26T09:00:00+00:00',live_trading=False,paid_actions=False,wallet_actions=False,next_decisive_test='Analyseer falsificatie');x.update(extra);p.write_text(json.dumps(x));return p

def setup(tmp_path,worker=None,clock=None):
    calls=[];repo=tmp_path/'repo'
    package=repo/'control/codex_supervisor';package.mkdir(parents=True,exist_ok=True)
    for name in ('supervisor.py','candidate_dispatch.py','evidence_wake.py','shadow_protocol.py','candidate_validation.py'):(package/name).write_bytes((ROOT/'control/codex_supervisor'/name).read_bytes())
    queue=repo/'control/hourly';queue.mkdir(parents=True,exist_ok=True);(queue/'candidate_queue.py').write_bytes((ROOT/'control/hourly/candidate_queue.py').read_bytes())
    tests=repo/'tests/codex_supervisor';tests.mkdir(parents=True,exist_ok=True);(tests/'test_shadow_protocol.py').write_bytes((ROOT/'tests/codex_supervisor/test_shadow_protocol.py').read_bytes())
    protocol_path=repo/'knowledge/candidates/protocols/MANUAL-SCOUT-HENGELTJES-20260924-shadow-v1.json';protocol_path.parent.mkdir(parents=True,exist_ok=True);protocol_path.write_bytes((ROOT/'knowledge/candidates/protocols/MANUAL-SCOUT-HENGELTJES-20260924-shadow-v1.json').read_bytes())
    import subprocess
    subprocess.run(['git','init','-b','main'],cwd=repo,capture_output=True,check=True)
    subprocess.run(['git','-c','user.name=Fixture','-c','user.email=fixture@localhost','add','--all'],cwd=repo,capture_output=True,check=True)
    subprocess.run(['git','-c','user.name=Fixture','-c','user.email=fixture@localhost','commit','-qm','test fixture'],cwd=repo,capture_output=True,check=True)
    def good(t,thread,folder,fd):
        calls.append(t['candidate_id'])
        final=dict(candidate_id=t['candidate_id'],queue_status='WAITING_FOR_DATA',finding='Geen data',next_action='Verzamel primaire evidence',scientific_status='NO_PROVEN_EDGE')
        events=[{'type':'thread.started','thread_id':'11111111-1111-1111-1111-111111111111'},{'type':'item.completed','item':{'type':'agent_message','text':json.dumps(final)}},{'type':'turn.completed'}]
        m.atomic(folder/'events.jsonl',''.join(json.dumps(e)+'\n' for e in events));return 0
    s=m.Supervisor(tmp_path/'runtime',worker or good,clock or (lambda:1000),candidate_source=lambda s:d.select_task(s,repo))
    return repo,s,calls,good

def test_complete_then_highest_eligible_then_empty(tmp_path):
    repo,s,calls,_=setup(tmp_path);candidate(repo,'FIRST','P0');assert s.tick()['state']=='COMPLETE'
    candidate(repo,'LOW','P3');candidate(repo,'HIGH','P1');candidate(repo,'WAIT','P0','WAITING_FOR_DATA')
    assert s.tick()['state']=='COMPLETE';assert calls==['FIRST','HIGH']
    assert s.tick()['state']=='COMPLETE';assert calls[-1]=='LOW'
    assert s.tick()['reason']=='QUEUE_EMPTY';assert s.tick()['state']=='IDLE';assert len(calls)==3

@pytest.mark.parametrize('status',['COMPLETE','RUNNING','PARKED','WATCH','WAITING_FOR_DATA','WAITING_FOR_RESULT','CLOSED_NEGATIVE'])
def test_nonactionable_skipped(tmp_path,status):
    repo,s,calls,_=setup(tmp_path);candidate(repo,status=status)
    assert s.tick()['reason']=='QUEUE_EMPTY';assert calls==[]

@pytest.mark.parametrize('gate',['human_gate','requires_human_approval','financial_gate','live_trading','paid_actions','wallet_actions'])
def test_gate_skipped(tmp_path,gate):
    repo,s,calls,_=setup(tmp_path);candidate(repo,**{gate:True})
    assert s.tick()['reason']=='QUEUE_EMPTY';assert not calls

def test_metadata_change_not_new_work(tmp_path):
    repo,s,calls,_=setup(tmp_path);p=candidate(repo);s.tick()
    x=json.loads(p.read_text());x['updated_at']='2026-09-27';x['priority']='P0';p.write_text(json.dumps(x))
    assert s.tick()['reason']=='QUEUE_EMPTY';assert calls==['A']

def test_busy_no_second_worker(tmp_path):
    repo,s,calls,_=setup(tmp_path);candidate(repo)
    with s.locked():
        with pytest.raises(m.Blocked,match='ALREADY'):s.tick()
    assert calls==[]

def test_selected_survives_crash_before_start(tmp_path,monkeypatch):
    repo,s,calls,_=setup(tmp_path);candidate(repo)
    original=s.views
    def crash():original();raise KeyboardInterrupt()
    monkeypatch.setattr(s,'views',crash)
    with pytest.raises(KeyboardInterrupt):s.tick()
    monkeypatch.setattr(s,'views',original)
    assert s.tick()['state']=='COMPLETE';s.tick();assert calls==['A']

def test_quota_resume_once(tmp_path):
    clock=[1000];repo,s,calls,good=setup(tmp_path,clock=lambda:clock[0]);candidate(repo);attempts=[]
    def worker(t,thread,folder,fd):
        attempts.append(thread)
        if len(attempts)==1:
            m.atomic(folder/'events.jsonl',json.dumps({'type':'thread.started','thread_id':'11111111-1111-1111-1111-111111111111'})+'\n'+json.dumps({'type':'error','message':'usage_limit'})+'\n');return 1
        return good(t,thread,folder,fd)
    s.worker=worker
    assert s.tick()['state']=='PAUSED_USAGE_LIMIT';s.tick();assert len(attempts)==1
    clock[0]+=18001;assert s.tick()['state']=='COMPLETE';s.tick();assert calls==['A'];assert attempts[1] is not None

def test_owner_source_unchanged_and_result_applied(tmp_path):
    repo,s,calls,_=setup(tmp_path);p=candidate(repo);before=p.read_bytes();s.tick()
    assert p.read_bytes()==before
    applied=list((s.root/'runs').glob('*/CANDIDATE_APPLIED.json'));assert len(applied)==1
    assert json.loads(applied[0].read_text())['queue_status']=='WAITING_FOR_DATA'

def test_source_changed_during_worker_fails_closed(tmp_path):
    repo,s,calls,good=setup(tmp_path);p=candidate(repo)
    def worker(t,thread,folder,fd):
        rc=good(t,thread,folder,fd);x=json.loads(p.read_text());x['next_decisive_test']='Owner wijziging';p.write_text(json.dumps(x));return rc
    s.worker=worker
    assert s.tick()['state']=='FAILED'
    assert not list((s.root/'runs').glob('*/CANDIDATE_APPLIED.json'))

def test_protocol_changed_during_reasoning_fails_closed(tmp_path):
    repo,s,_,good=setup(tmp_path);candidate(repo,prospective_protocols=['knowledge/candidates/protocols/protocol-v1.json']);protocol=heng_protocol(repo)
    with s.locked():task=d.select_task(s,repo)
    final=json.dumps({'candidate_id':'A','queue_status':'WAITING_FOR_DATA','finding':'f','next_action':'n','scientific_status':'NO_PROVEN_EDGE'})
    protocol.write_text(protocol.read_text().replace('PREREGISTERED_PENDING_DEATHCHECKS','PREREGISTERED_PENDING_DEATHCHECKS_CHANGED'))
    with pytest.raises(ValueError,match='CHANGED'):d.validate_result(task,final)

def test_malformed_result_not_applied_or_retried(tmp_path):
    repo,s,calls,good=setup(tmp_path);candidate(repo);attempts=[]
    def bad(t,thread,folder,fd):
        attempts.append(1);m.atomic(folder/'events.jsonl',json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'not JSON'}})+'\n'+json.dumps({'type':'turn.completed'})+'\n');return 0
    s.worker=bad;assert s.tick()['state']=='FAILED';assert s.tick()['reason']=='QUEUE_EMPTY';assert len(attempts)==1

def test_complete_task_then_existing_queued_task(tmp_path):
    repo,s,calls,good=setup(tmp_path);candidate(repo,'A');assert s.tick()['state']=='COMPLETE'
    candidate(repo,'B')
    with s.locked():next_task=d.select_task(s,repo)
    s.enqueue(next_task)
    assert s.tick()['state']=='COMPLETE';assert calls==['A','B']

def heng_protocol(repo):
    original=json.loads((ROOT/'knowledge/candidates/protocols/MANUAL-SCOUT-HENGELTJES-20260924-shadow-v1.json').read_text())
    original['candidate_id']='A';p=repo/'knowledge/candidates/protocols/protocol-v1.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(original));return p

def test_prospective_protocol_content_is_hashed_and_prompted(tmp_path):
    repo,s,_,_=setup(tmp_path);candidate(repo,prospective_protocols=['knowledge/candidates/protocols/protocol-v1.json']);p=heng_protocol(repo)
    with s.locked():t=d.select_task(s,repo)
    assert json.loads(t['referenced_evidence']['knowledge/candidates/protocols/protocol-v1.json'])['status']=='PREREGISTERED_PENDING_DEATHCHECKS'
    assert 'DC1_FALSE_POSITIVE_FILL' in t['prompt']
    assert t['candidate_source_hashes']['knowledge/candidates/protocols/protocol-v1.json']==m.digest(p.read_bytes())

def test_unsafe_protocol_path_and_symlink_rejected(tmp_path):
    repo,s,_,_=setup(tmp_path);candidate(repo,prospective_protocols=['../outside.json'])
    with s.locked(),pytest.raises(ValueError,match='UNSAFE'):d.select_task(s,repo)
    repo2,s2,_,_=setup(tmp_path/'two');candidate(repo2,prospective_protocols=['knowledge/candidates/protocols/protocol-v1.json']);p=heng_protocol(repo2);p.unlink();p.symlink_to(PROTOCOL)
    with s2.locked(),pytest.raises(ValueError,match='SYMLINK'):d.select_task(s2,repo2)

def test_protocol_change_creates_new_review_version(tmp_path):
    repo,s,_,_=setup(tmp_path);candidate(repo,prospective_protocols=['knowledge/candidates/protocols/protocol-v1.json']);p=heng_protocol(repo)
    with s.locked():one=d.select_task(s,repo)
    p.write_text(p.read_text().replace('PREREGISTERED_PENDING_DEATHCHECKS','PREREGISTERED_PENDING_DEATHCHECKS_V2'))
    with s.locked():two=d.select_task(s,repo)
    assert one['task_id']!=two['task_id']

def test_waiting_data_without_local_step_is_idle(tmp_path):
    repo,s,calls,_=setup(tmp_path);candidate(repo)
    assert s.tick()['state']=='COMPLETE';assert s.tick()['reason']=='QUEUE_EMPTY';assert calls==['A']
    assert json.loads(next((s.root/'candidate_states').glob('*.json')).read_text())['queue_status']=='WAITING_FOR_DATA'

def test_needs_revision_is_human_blocked_not_queue_empty(tmp_path):
    repo=tmp_path/'repo';(repo/'knowledge/candidates').mkdir(parents=True)
    root=tmp_path/'runtime';states=root/'candidate_states';states.mkdir(parents=True)
    (states/'candidate-v1.json').write_text(json.dumps({'candidate_id':'C-1','queue_status':'NEEDS_REVISION'}))
    s=m.Supervisor(root,worker=lambda *a:0,candidate_source=lambda current:d.select_next(current,repo))
    decision=s.tick()
    assert decision['state']=='BLOCKED' and decision['reason']=='NEEDS_REVISION_REQUIRES_NEW_VERSION_AND_REVIEW'
    assert decision['next_action']=='Nieuwe protocolversie en Director-herbeoordeling vereist'

def test_protocol_pending_overrides_idle_to_deterministic_build_handoff(tmp_path):
    repo,s,calls,_=setup(tmp_path);candidate(repo,prospective_protocols=['knowledge/candidates/protocols/protocol-v1.json']);heng_protocol(repo)
    # Director cannot suppress required registered gates with WAITING_FOR_DATA.
    assert s.tick()['state']=='COMPLETE';overlay=json.loads(next((s.root/'candidate_states').glob('*.json')).read_text())
    assert overlay['queue_status']=='NEEDS_BUILD' and overlay['build_handoff']['operation']=='PROTOCOL_DEATHCHECK_VALIDATION'

def test_duplicate_application_idempotent_and_next_action_is_data(tmp_path):
    repo,s,_,_=setup(tmp_path);candidate(repo);s.tick();run=next((s.root/'runs').glob('CANDIDATE-*'));t=json.loads((run/'TASK.json').read_text());result=d.validate_result(t,json.loads((run/'COMPLETE.json').read_text())['final'])
    overlay,record,already=d.apply_candidate_result(s,t,result,m.digest(json.loads((run/'COMPLETE.json').read_text())['final'].encode()),1000)
    assert already and overlay.is_file();assert record['completion_hash']==m.digest(json.loads((run/'COMPLETE.json').read_text())['final'].encode())
    assert json.loads((repo/'knowledge/candidates/A.json').read_text())['candidate_id']=='A'

def test_failed_deathcheck_cannot_authorize_activation():
    import shadow_protocol as p
    protocol=json.loads(PROTOCOL.read_text());protocol['safety']['paid_actions']=True
    with pytest.raises(ValueError):p.run_deathchecks({'candidate_id':protocol['candidate_id']},protocol,{},'commit')

def test_all_unit_gates_pass_still_no_prospective_activation():
    import shadow_protocol as p
    protocol=json.loads(PROTOCOL.read_text());r=p.run_deathchecks({'candidate_id':protocol['candidate_id']},protocol,{'protocol':'hash'},'commit')
    assert r['all_deathchecks_pass'] and r['miami_regression_fixture']['pass']
    assert r['activation_authorized'] is False and r['prospective_evidence'] is False

@pytest.mark.parametrize('gate',[{'live_trading':True},{'paid_actions':True},{'wallet_actions':True},{'human_gate':True}])
def test_human_or_safety_gate_skips_candidate(tmp_path,gate):
    repo,s,calls,_=setup(tmp_path);candidate(repo,**gate);assert s.tick()['reason']=='QUEUE_EMPTY';assert not calls

def test_pending_protocol_build_validation_runs_three_pinned_clean_suites(tmp_path):
    import candidate_validation as v
    repo,s,calls,_=setup(tmp_path);candidate(repo,prospective_protocols=['knowledge/candidates/protocols/protocol-v1.json']);heng_protocol(repo)
    assert s.tick()['state']=='COMPLETE'
    with s.locked():t=d.pending_validation_task(s,repo)
    assert t and t['local_operation']=='PROTOCOL_DEATHCHECK_VALIDATION'
    folder=s.root/'runs'/f"{t['task_id']}-1-test";folder.mkdir(parents=True)
    report=v.run(t,repo,folder)
    assert report['status']=='PASS' and report['local_test_runs']==3 and report['local_test_runs_passed']==3 and report['prospective_clean_runs']==0 and report['prospective_runs']==0
    t['run_path']=str(folder.relative_to(s.root))
    overlay=json.loads(pathlib.Path(t['overlay_path']).read_text());_,updated=d.apply_validation(s,t,report)
    assert updated['queue_status']=='VALIDATION' and updated['activation']['authorized'] is False
    assert not list((repo/'knowledge/candidates').glob('*.tmp'))

def test_validation_requires_durable_in_root_report(tmp_path):
    import candidate_validation as v
    repo,s,_,_=setup(tmp_path);candidate(repo,prospective_protocols=['knowledge/candidates/protocols/protocol-v1.json']);heng_protocol(repo)
    s.tick()
    with s.locked():task=d.pending_validation_task(s,repo)
    folder=s.root/'runs'/'valid-report';folder.mkdir(parents=True);report=v.run(task,repo,folder)
    task['run_path']='runs/missing'
    with pytest.raises(ValueError,match='NOT_DURABLE'):d.apply_validation(s,task,report)

def test_validation_report_cannot_be_replayed_across_task_or_enable_activation(tmp_path):
    import candidate_validation
    repo,s,_,_=setup(tmp_path);candidate(repo,prospective_protocols=['knowledge/candidates/protocols/protocol-v1.json']);heng_protocol(repo)
    s.tick()
    with s.locked():task=d.pending_validation_task(s,repo)
    folder=s.root/'runs'/'valid-report';folder.mkdir(parents=True);good=candidate_validation.run(task,repo,folder)
    with pytest.raises(ValueError,match='BINDING'):d.apply_validation(s,task,{**good,'task_id':'OTHER'})
    with pytest.raises(ValueError,match='NOT_PASS'):d.apply_validation(s,task,{**good,'activation_authorized':True})


def wake_condition(kind,**extra):
    return {'schema':'PVA_EVIDENCE_WAKE_CONDITION_V1','evidence_kinds':[kind],**extra}


def waiting_canary(tmp_path,cid,status,condition,condition_key='evidence_wake_condition'):
    import time
    clock=[time.time()-60]
    repo,s,calls,_=setup(tmp_path,clock=lambda:clock[0])
    extra={condition_key:condition}
    candidate(repo,cid,'P1','NEEDS_DIRECTOR',**extra)
    def worker(t,thread,folder,fd):
        calls.append(t['candidate_id'])
        state=status if len(calls)==1 else 'WAITING_FOR_DATA'
        final=dict(candidate_id=t['candidate_id'],queue_status=state,finding='Fixture-only test evidence',next_action='Beoordeel uitsluitend nieuwe fixture evidence',scientific_status='NO_PROVEN_EDGE')
        events=[{'type':'thread.started','thread_id':'fixture-thread'},{'type':'item.completed','item':{'type':'agent_message','text':json.dumps(final)}},{'type':'turn.completed'}]
        m.atomic(folder/'events.jsonl',''.join(json.dumps(e)+'\n' for e in events));return 0
    s.worker=worker
    assert s.tick()['state']=='COMPLETE'
    clock[0]+=10
    return repo,s,calls,clock


def write_candidate_evidence(repo,cid,kind,**extra):
    import datetime as dt
    now=dt.datetime.now(dt.timezone.utc)
    evidence_id='fixture-'+str(len(list((repo/'knowledge/evidence/candidate_events').glob('*.json'))) if (repo/'knowledge/evidence/candidate_events').exists() else 0)
    manifest={'schema':'PVA_IMMUTABLE_EVIDENCE_MANIFEST_V1','source_ref':'fixture://point-in-time-source/'+evidence_id,'source_sha256':'a'*64,
              'retrieved_at':(now-dt.timedelta(seconds=10)).isoformat(),'archived_at':(now-dt.timedelta(seconds=5)).isoformat(),'backfill':False}
    mp=repo/'knowledge/evidence/manifests'/(evidence_id+'.json');mp.parent.mkdir(parents=True,exist_ok=True);mb=json.dumps(manifest,sort_keys=True).encode();mp.write_bytes(mb)
    doc={'schema':'PVA_CANDIDATE_EVIDENCE_V1','evidence_id':'fixture-'+str(len(list((repo/'knowledge/evidence/candidate_events').glob('*.json'))) if (repo/'knowledge/evidence/candidate_events').exists() else 0),
         'candidate_id':cid,'evidence_kind':kind,'status':'VALID','evidence_timestamp':(now-dt.timedelta(seconds=3)).isoformat(),
         'available_at':(now-dt.timedelta(seconds=2)).isoformat(),'archived_at':now.isoformat(),'backfill':False,
         'source_manifest_ref':str(mp.relative_to(repo)),'source_manifest_sha256':m.digest(mb),**extra}
    p=repo/'knowledge/evidence/candidate_events'/(doc['evidence_id']+'.json');p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(doc,sort_keys=True));return p


@pytest.mark.parametrize('kind,condition,artifact,initial_state',[
    ('kwi_evaluator_result',wake_condition('kwi_evaluator_result',minimum_groups=2,minimum_scorable_pairs_per_group=30,required_status='VALID'),{'scorable_pairs_by_group':{'CITY-A':0,'CITY-B':0}},'WAITING_FOR_RESULT'),
    ('asset_fill_result',wake_condition('asset_fill_result',minimum_full_fills=1,require_conservative_proof=True,required_hash_fields=['full_fill_evidence_sha256']),{'conservative_full_fills':0,'conservative_proof':False},'RUNNING'),
    ('weather_observation',wake_condition('statewise_rule_portfolio'),{},'WAITING_FOR_DATA'),
])
def test_canary_irrelevant_or_insufficient_evidence_does_not_wake(tmp_path,kind,condition,artifact,initial_state):
    repo,s,calls,_=waiting_canary(tmp_path,'CANARY',initial_state,condition)
    write_candidate_evidence(repo,'CANARY',kind,**artifact)
    assert s.tick()['reason']=='QUEUE_EMPTY'
    assert calls==['CANARY']
    assert not list((s.root/'candidate_wakes').glob('*.json'))


@pytest.mark.parametrize('cid,state,condition,kind,fields',[
    ('KWI-FULL-STATION-PRECANONICAL-V1','WAITING_FOR_RESULT',wake_condition('kwi_evaluator_result',minimum_groups=2,minimum_scorable_pairs_per_group=30,required_status='VALID'),'kwi_evaluator_result',{'scorable_pairs_by_group':{'CITY-A':30,'CITY-B':30}}),
    ('ASSET-RANK-MAKER-HEDGE-V1','RUNNING',wake_condition('asset_fill_result',minimum_full_fills=1,require_conservative_proof=True,required_hash_fields=['full_fill_evidence_sha256']),'asset_fill_result',{'conservative_full_fills':1,'conservative_proof':True,'full_fill_evidence_sha256':'b'*64}),
    ('PAYOFF-IDENTITY-MINING-V1','WAITING_FOR_DATA',wake_condition('statewise_rule_portfolio',required_status='VALID',required_hash_fields=['portfolio_sha256','rule_sha256']),'statewise_rule_portfolio',{'portfolio_sha256':'a'*64,'rule_sha256':'c'*64}),
])
def test_typed_post_cutoff_evidence_wakes_canary_once(tmp_path,cid,state,condition,kind,fields):
    repo,s,calls,clock=waiting_canary(tmp_path,cid,state,condition)
    # An unrelated weather artifact is discovered but cannot match the payoff condition.
    if cid=='PAYOFF-IDENTITY-MINING-V1':
        write_candidate_evidence(repo,cid,'weather_observation')
        assert s.tick()['reason']=='QUEUE_EMPTY'
        clock[0]+=10
    write_candidate_evidence(repo,cid,kind,**fields)
    assert s.tick()['state']=='COMPLETE'
    assert calls==[cid,cid]
    wakes=list((s.root/'candidate_wakes').glob('*.json'))
    assert len(wakes)==1
    wake=json.loads(wakes[0].read_text())
    assert wake['candidate_id']==cid and wake['scientific_status']=='NO_PROVEN_EDGE'
    assert s.tick()['reason']=='QUEUE_EMPTY'
    assert calls==[cid,cid]


def test_heng_revision_wakes_only_on_new_protocol_revision_artifact(tmp_path):
    condition=wake_condition('protocol_revision',protocol_ref='knowledge/candidates/protocols/protocol-v1.json')
    repo,s,calls,_=waiting_canary(tmp_path,'MANUAL-SCOUT-HENGELTJES-20260924','NEEDS_REVISION',condition,'resurrection_condition')
    write_candidate_evidence(repo,'MANUAL-SCOUT-HENGELTJES-20260924','hourly_weather')
    assert s.tick()['reason']=='QUEUE_EMPTY'
    p=write_candidate_evidence(repo,'MANUAL-SCOUT-HENGELTJES-20260924','protocol_revision',protocol_ref='knowledge/candidates/protocols/protocol-v1.json',protocol_sha256='b'*64,prior_protocol_sha256='a'*64)
    assert s.tick()['state']=='COMPLETE'
    assert calls==['MANUAL-SCOUT-HENGELTJES-20260924']*2
    assert len(list((s.root/'candidate_wakes').glob('*.json')))==1


def test_evidence_before_cutoff_mutation_symlink_and_free_text_fail_closed(tmp_path):
    import datetime as dt
    repo,s,calls,clock=waiting_canary(tmp_path,'CANARY','WAITING_FOR_DATA',wake_condition('statewise_rule_portfolio'))
    p=write_candidate_evidence(repo,'CANARY','statewise_rule_portfolio')
    doc=json.loads(p.read_text());old=(dt.datetime.fromtimestamp(clock[0]-20,dt.timezone.utc)).isoformat();doc.update(evidence_timestamp=old,available_at=old,archived_at=dt.datetime.now(dt.timezone.utc).isoformat())
    mp=repo/doc['source_manifest_ref'];manifest=json.loads(mp.read_text());old_dt=dt.datetime.fromisoformat(old);manifest.update(retrieved_at=(old_dt-dt.timedelta(seconds=10)).isoformat(),archived_at=(old_dt-dt.timedelta(seconds=5)).isoformat());mb=json.dumps(manifest,sort_keys=True).encode();mp.write_bytes(mb);doc['source_manifest_sha256']=m.digest(mb);p.write_text(json.dumps(doc))
    assert s.tick()['reason']=='QUEUE_EMPTY'
    doc.update(evidence_timestamp=dt.datetime.now(dt.timezone.utc).isoformat(),available_at=dt.datetime.now(dt.timezone.utc).isoformat(),archived_at=dt.datetime.now(dt.timezone.utc).isoformat());p.write_text(json.dumps(doc))
    with s.locked():task=d.select_next(s,repo)
    p.write_text(p.read_text()+' ')
    with pytest.raises(ValueError,match='CHANGED'):d.validate_result(task,json.dumps({'candidate_id':'CANARY','queue_status':'WAITING_FOR_DATA','finding':'f','next_action':'n','scientific_status':'NO_PROVEN_EDGE'}))
    p.unlink()
    outside=repo/'outside.json';outside.write_text('{}');link=repo/'knowledge/experiment_results'/'link.json';link.parent.mkdir(parents=True,exist_ok=True);link.symlink_to(outside)
    with s.locked(),pytest.raises(ValueError,match='SYMLINK'):d.select_next(s,repo)


def test_wake_record_crash_recovery_and_new_hash_are_exactly_once(tmp_path,monkeypatch):
    repo,s,calls,clock=waiting_canary(tmp_path,'CANARY','WAITING_FOR_RESULT',wake_condition('kwi_evaluator_result',minimum_scorable_pairs=1))
    write_candidate_evidence(repo,'CANARY','kwi_evaluator_result',scorable_pairs=2)
    original=m.validate_task;raised=[False]
    def crash(task):
        if task.get('candidate_wake') and not raised[0]:
            raised[0]=True;raise KeyboardInterrupt()
        return original(task)
    monkeypatch.setattr(m,'validate_task',crash)
    with pytest.raises(KeyboardInterrupt):s.tick()
    assert len(list((s.root/'candidate_wakes').glob('*.json')))==1 and calls==['CANARY']
    monkeypatch.setattr(m,'validate_task',original)
    assert s.tick()['state']=='COMPLETE';assert calls==['CANARY','CANARY']
    s.tick();assert calls==['CANARY','CANARY']
    clock[0]+=10
    write_candidate_evidence(repo,'CANARY','kwi_evaluator_result',scorable_pairs=3)
    assert s.tick()['state']=='COMPLETE';assert calls==['CANARY','CANARY','CANARY']


def test_waiting_candidate_protocol_hash_change_creates_new_review(tmp_path):
    repo,s,calls,_=setup(tmp_path)
    p=candidate(repo,'WAITING-PROTOCOL','P1','NEEDS_DIRECTOR',prospective_protocols=['knowledge/candidates/protocols/protocol-v1.json'])
    protocol=repo/'knowledge/candidates/protocols/protocol-v1.json';protocol.parent.mkdir(parents=True,exist_ok=True);protocol.write_text(json.dumps({'protocol_id':'v1','status':'ACTIVE'}))
    assert s.tick()['state']=='COMPLETE'
    x=json.loads(p.read_text());x['queue_status']='WAITING_FOR_RESULT';p.write_text(json.dumps(x))
    protocol.write_text(json.dumps({'protocol_id':'v2','status':'ACTIVE'}))
    assert s.tick()['state']=='COMPLETE'
    assert calls==['WAITING-PROTOCOL','WAITING-PROTOCOL']


def test_overlay_mutation_during_wake_reasoning_fails_closed(tmp_path):
    repo,s,calls,_=waiting_canary(tmp_path,'CANARY','WAITING_FOR_DATA',wake_condition('statewise_rule_portfolio'))
    write_candidate_evidence(repo,'CANARY','statewise_rule_portfolio')
    with s.locked():task=d.select_next(s,repo)
    prior=pathlib.Path(task['candidate_runtime_root'])/task['wake_record']['previous_overlay']
    prior.write_text(prior.read_text()+' ')
    with pytest.raises(ValueError,match='OVERLAY_CHANGED'):
        d.validate_result(task,json.dumps({'candidate_id':'CANARY','queue_status':'WAITING_FOR_DATA','finding':'f','next_action':'n','scientific_status':'NO_PROVEN_EDGE'}))


def test_protocol_mutation_after_wake_selection_fails_closed(tmp_path):
    repo,s,calls,_=setup(tmp_path)
    p=candidate(repo,'CANARY','P1','NEEDS_DIRECTOR',prospective_protocols=['knowledge/candidates/protocols/p.json'],evidence_wake_condition=wake_condition('kwi_evaluator_result',minimum_scorable_pairs=1))
    protocol=repo/'knowledge/candidates/protocols/p.json';protocol.parent.mkdir(parents=True,exist_ok=True);protocol.write_text(json.dumps({'protocol_id':'p-v1'}))
    def worker(t,thread,folder,fd):
        calls.append(t['candidate_id']);final={'candidate_id':'CANARY','queue_status':'WAITING_FOR_RESULT','finding':'waiting','next_action':'wacht op resultaat','scientific_status':'NO_PROVEN_EDGE'}
        events=[{'type':'thread.started','thread_id':'t'},{'type':'item.completed','item':{'type':'agent_message','text':json.dumps(final)}},{'type':'turn.completed'}];m.atomic(folder/'events.jsonl',''.join(json.dumps(x)+'\n' for x in events));return 0
    s.worker=worker;assert s.tick()['state']=='COMPLETE'
    write_candidate_evidence(repo,'CANARY','kwi_evaluator_result',scorable_pairs=1)
    with s.locked():task=d.select_next(s,repo)
    protocol.write_text(json.dumps({'protocol_id':'p-v2'}))
    with pytest.raises(ValueError,match='CANDIDATE_SOURCE_CHANGED'):
        d.validate_result(task,json.dumps({'candidate_id':'CANARY','queue_status':'WAITING_FOR_DATA','finding':'f','next_action':'n','scientific_status':'NO_PROVEN_EDGE'}))


def test_source_waiting_candidate_registers_only_explicit_typed_condition(tmp_path):
    import datetime as dt
    repo,s,calls,_=setup(tmp_path)
    cutoff=(dt.datetime.now(dt.timezone.utc)-dt.timedelta(seconds=30)).isoformat()
    condition=wake_condition('statewise_rule_portfolio',cutoff=cutoff,required_status='VALID')
    p=candidate(repo,'SOURCE-WAITER','P1','WAITING_FOR_DATA',resume_condition=condition)
    before=p.read_bytes();write_candidate_evidence(repo,'SOURCE-WAITER','statewise_rule_portfolio')
    assert s.tick()['state']=='COMPLETE'
    assert calls==['SOURCE-WAITER'] and p.read_bytes()==before
    assert len(list((s.root/'candidate_wakes').glob('*.json')))==1


def test_source_waiting_free_text_condition_never_registers_or_wakes(tmp_path):
    repo,s,calls,_=setup(tmp_path)
    candidate(repo,'SOURCE-WAITER','P1','WAITING_FOR_DATA',resume_condition='when useful new data appears')
    write_candidate_evidence(repo,'SOURCE-WAITER','statewise_rule_portfolio')
    assert s.tick()['reason']=='QUEUE_EMPTY'
    assert calls==[] and not list((s.root/'candidate_states').glob('*.json'))


def test_fixture_canary_emits_ordered_wake_to_result_events(tmp_path,capsys):
    repo,s,calls,_=waiting_canary(tmp_path,'CANARY','WAITING_FOR_DATA',wake_condition('statewise_rule_portfolio'))
    capsys.readouterr()
    write_candidate_evidence(repo,'CANARY','statewise_rule_portfolio')
    assert s.tick()['state']=='COMPLETE'
    output=capsys.readouterr().out
    events=[json.loads(line).get('event') for line in output.splitlines() if line.startswith('{')]
    expected=['EVIDENCE_DISCOVERED','EVIDENCE_MATCHED','CANDIDATE_WAKE_RECORDED','NEXT_TASK_SELECTED','TASK_QUEUED','WORKER_START','RESULT_APPLIED_NEXT_ACTION_RECORDED']
    positions=[events.index(name) for name in expected]
    assert positions==sorted(positions) and calls==['CANARY','CANARY']


def test_multiple_wakes_follow_existing_candidate_priority(tmp_path):
    import datetime as dt,time
    clock=[time.time()-60];repo=tmp_path/'repo';pkg=repo/'control/codex_supervisor';pkg.mkdir(parents=True)
    for name in ('supervisor.py','candidate_dispatch.py','evidence_wake.py','shadow_protocol.py','candidate_validation.py'):(pkg/name).write_bytes((ROOT/'control/codex_supervisor'/name).read_bytes())
    q=repo/'control/hourly';q.mkdir(parents=True);(q/'candidate_queue.py').write_bytes((ROOT/'control/hourly/candidate_queue.py').read_bytes())
    import subprocess
    subprocess.run(['git','init','-b','main'],cwd=repo,capture_output=True,check=True)
    subprocess.run(['git','-c','user.name=Fixture','-c','user.email=fixture@localhost','add','--all'],cwd=repo,capture_output=True,check=True)
    subprocess.run(['git','-c','user.name=Fixture','-c','user.email=fixture@localhost','commit','-qm','fixture'],cwd=repo,capture_output=True,check=True)
    condition=wake_condition('statewise_rule_portfolio')
    candidate(repo,'LOW','P3','NEEDS_DIRECTOR',evidence_wake_condition=condition)
    candidate(repo,'HIGH','P1','NEEDS_DIRECTOR',evidence_wake_condition=condition)
    calls=[]
    def worker(t,thread,folder,fd):
        calls.append(t['candidate_id']);final={'candidate_id':t['candidate_id'],'queue_status':'WAITING_FOR_DATA','finding':'wait','next_action':'wacht','scientific_status':'NO_PROVEN_EDGE'}
        es=[{'type':'thread.started','thread_id':'t'},{'type':'item.completed','item':{'type':'agent_message','text':json.dumps(final)}},{'type':'turn.completed'}];m.atomic(folder/'events.jsonl',''.join(json.dumps(e)+'\n' for e in es));return 0
    s=m.Supervisor(tmp_path/'runtime',worker,lambda:clock[0],candidate_source=lambda current:d.select_next(current,repo))
    assert s.tick()['state']=='COMPLETE' and calls==['HIGH']
    clock[0]+=1;assert s.tick()['state']=='COMPLETE' and calls==['HIGH','LOW']
    write_candidate_evidence(repo,'HIGH','statewise_rule_portfolio');write_candidate_evidence(repo,'LOW','statewise_rule_portfolio')
    clock[0]+=10;assert s.tick()['state']=='COMPLETE' and calls[-1]=='HIGH'


def test_waiting_candidate_does_not_block_other_queue_work(tmp_path):
    repo,s,calls,clock=waiting_canary(tmp_path,'WAITER','WAITING_FOR_DATA',wake_condition('statewise_rule_portfolio'))
    candidate(repo,'OTHER','P1','NEEDS_DIRECTOR')
    assert s.tick()['state']=='COMPLETE'
    assert calls==['WAITER','OTHER']
