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
    for name in ('supervisor.py','candidate_dispatch.py','shadow_protocol.py','candidate_validation.py'):(package/name).write_bytes((ROOT/'control/codex_supervisor'/name).read_bytes())
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
