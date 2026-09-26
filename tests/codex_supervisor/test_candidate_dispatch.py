import json,pathlib,sys
import pytest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'control/codex_supervisor'))
import supervisor as m
import candidate_dispatch as d

def candidate(repo,cid='A',priority='P2',status='NEEDS_DIRECTOR',**extra):
    p=repo/'knowledge/candidates'/f'{cid}.json';p.parent.mkdir(parents=True,exist_ok=True)
    x=dict(candidate_id=cid,priority=priority,queue_status=status,created_at='2026-09-26T09:00:00+00:00',queue_entered_at='2026-09-26T09:00:00+00:00',live_trading=False,paid_actions=False,wallet_actions=False,next_decisive_test='Analyseer falsificatie');x.update(extra);p.write_text(json.dumps(x));return p

def setup(tmp_path,worker=None,clock=None):
    calls=[];repo=tmp_path/'repo'
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
    assert json.loads(applied[0].read_text())['result']['queue_status']=='WAITING_FOR_DATA'

def test_source_changed_during_worker_fails_closed(tmp_path):
    repo,s,calls,good=setup(tmp_path);p=candidate(repo)
    def worker(t,thread,folder,fd):
        rc=good(t,thread,folder,fd);x=json.loads(p.read_text());x['next_decisive_test']='Owner wijziging';p.write_text(json.dumps(x));return rc
    s.worker=worker
    assert s.tick()['state']=='FAILED'
    assert not list((s.root/'runs').glob('*/CANDIDATE_APPLIED.json'))

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
