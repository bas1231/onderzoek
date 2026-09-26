import importlib.util,json,os,subprocess,sys,time
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('supervisor',ROOT/'control/codex_supervisor/supervisor.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def task(id='TASK-A',priority=90):
    prompt='Beoordeel publieke evidence; geen tools.'
    return dict(task_id=id,task_class='research_review',priority=priority,expected_value=10,estimated_reasoning_cost=1,created_at='2026-09-25',prompt=prompt,input_sha256=m.digest(prompt.encode()))
def emit(folder,events):m.atomic(folder/'events.jsonl',''.join(json.dumps(e)+'\n' for e in events))
GOOD=[{'type':'thread.started','thread_id':'11111111-1111-1111-1111-111111111111'},{'type':'item.completed','item':{'type':'agent_message','text':'NO_PROVEN_EDGE: NEEDS_DATA'}},{'type':'turn.completed'}]

def test_pause_resume_same_task_and_deduplicate(tmp_path):
    clock=[1000];calls=[]
    def worker(t,thread,folder,fd):
        calls.append((t['task_id'],thread))
        if len(calls)==1:emit(folder,[GOOD[0],{'type':'error','message':"You've hit your usage limit"}]);return 1
        emit(folder,GOOD);return 0
    s=m.Supervisor(tmp_path,worker,lambda:clock[0]);s.enqueue(task())
    assert s.tick()['state']=='PAUSED_USAGE_LIMIT'
    assert s.tick()['state']=='PAUSED_USAGE_LIMIT' and len(calls)==1
    s.enqueue(task('TASK-B',1)) # enqueue cannot reset global quota pause
    assert json.loads((tmp_path/'STATE.json').read_text())['state']=='PAUSED_USAGE_LIMIT'
    assert s.tick()['state']=='PAUSED_USAGE_LIMIT' and len(calls)==1
    clock[0]+=18001
    assert s.tick()['state']=='COMPLETE';assert calls[1]==('TASK-A',GOOD[0]['thread_id'])
    s.enqueue(task());assert s.tick('CONSERVE')['state']=='IDLE';assert len(calls)==2
    assert json.loads((tmp_path/'STATE.json').read_text())['state'] in ('COMPLETE','IDLE')

def test_no_duplicate_expensive_work(tmp_path):
    calls=[]
    def worker(t,thread,folder,fd):calls.append(1);emit(folder,GOOD);return 0
    s=m.Supervisor(tmp_path,worker);s.enqueue(task());s.tick();s.enqueue(task());s.tick();assert calls==[1]

def test_recover_completed_events_after_supervisor_crash(tmp_path):
    def crash(t,thread,folder,fd):emit(folder,GOOD);raise KeyboardInterrupt()
    s=m.Supervisor(tmp_path,crash);s.enqueue(task())
    with pytest.raises(KeyboardInterrupt):s.tick()
    s.worker=lambda *a:pytest.fail('completed task must not execute again')
    assert s.tick()['state']=='COMPLETE'

def test_partial_event_is_not_success(tmp_path):
    def crash(t,thread,folder,fd):m.atomic(folder/'events.jsonl','{"type":"turn.completed"');raise KeyboardInterrupt()
    s=m.Supervisor(tmp_path,crash);s.enqueue(task())
    with pytest.raises(KeyboardInterrupt):s.tick()
    assert s.tick()['state']=='WAITING_RETRY'

def test_corrupt_state_fails_closed(tmp_path):
    s=m.Supervisor(tmp_path,lambda *a:pytest.fail('no work'));s.enqueue(task());(tmp_path/'STATE.json').write_text('{')
    with pytest.raises(m.Blocked,match='CORRUPT_STATE'):s.tick()
@pytest.mark.parametrize('filename',['TASK_QUEUE.jsonl','CONTINUATION.json'])
def test_corrupt_queue_and_continuation_fail_closed(tmp_path,filename):
    s=m.Supervisor(tmp_path,lambda *a:pytest.fail('no work'));s.enqueue(task());(tmp_path/filename).write_text('{')
    with pytest.raises(m.Blocked):s.tick()

def test_lock_conflict_and_stale_file(tmp_path):
    s=m.Supervisor(tmp_path);s.enqueue(task());(tmp_path/'worker.lock').write_text('stale PID1234')
    with s.locked():
        with pytest.raises(m.Blocked,match='ALREADY'):m.Supervisor(tmp_path).tick()
    # flock ownership, not PID text, determines staleness.
    assert s.tick('CRITICAL')['reason']=='CRITICAL_NO_NEW_WORK'

def test_lock_survives_parent_crash_until_worker_exits(tmp_path):
    code='''import fcntl,os,subprocess,sys
f=open(sys.argv[1],"a+");fcntl.flock(f,fcntl.LOCK_EX)
p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(2)"],pass_fds=(f.fileno(),))
print(p.pid,flush=True)
os._exit(1)
'''
    parent=subprocess.Popen([sys.executable,'-c',code,str(tmp_path/'worker.lock')],stdout=subprocess.PIPE,text=True);pid=int(parent.stdout.readline());parent.wait()
    with pytest.raises(m.Blocked,match='ALREADY'):m.Supervisor(tmp_path).tick()
    os.kill(pid,15)

def test_owner_sentinel_and_index_untouched(tmp_path):
    owner=tmp_path/'owner';owner.mkdir();(owner/'index').write_bytes(b'owner index');(owner/'work').write_bytes(b'owner work')
    before={p:p.read_bytes() for p in owner.iterdir()}
    def worker(t,thread,folder,fd):emit(folder,GOOD);return 0
    s=m.Supervisor(tmp_path/'runtime',worker);s.enqueue(task());s.tick()
    assert all(p.read_bytes()==v for p,v in before.items())
@pytest.mark.parametrize('change',[{'prompt':'changed'},{'priority':float('nan')},{'task_id':'../x'},{'estimated_reasoning_cost':0}])
def test_malformed_task_and_provenance(change,tmp_path):
    t=task();t.update(change)
    with pytest.raises(m.Blocked):m.Supervisor(tmp_path).enqueue(t)

def test_agent_prose_about_usage_is_not_usage_limit():
    e=[{'type':'item.completed','item':{'type':'agent_message','text':'usage limit is a topic'}},{'type':'turn.completed'}]
    assert m.classify(e,0)[0]=='COMPLETE'

def test_reasoning_worker_cli_is_restricted(tmp_path,monkeypatch):
    cache=tmp_path/'.codex';cache.mkdir();(cache/'models_cache.json').write_text(json.dumps({'models':[{'slug':'available-model','visibility':'list','priority':1}]}))
    monkeypatch.setattr(m.P,'home',classmethod(lambda cls:tmp_path))
    monkeypatch.setattr(m.subprocess,'run',lambda *a,**k:subprocess.CompletedProcess(a,0,'Logged in using ChatGPT',''))
    class Process:
        pid=123;returncode=0
        def communicate(self,*a,**k):return None
    def popen(args,**kw):
        assert '--ignore-user-config' in args and '--ignore-rules' in args
        assert 'sandbox_mode="read-only"' in args and 'approval_policy="never"' in args
        assert 'shell_tool' in args and 'apps' in args and 'web_search="disabled"' in args
        assert not any('API_KEY' in k for k in kw['env']);assert kw['pass_fds']==(7,)
        return Process()
    monkeypatch.setattr(m.subprocess,'Popen',popen)
    assert m.CodexWorker('codex')(task(),None,tmp_path,7)==0

def test_followup_uses_exact_completed_session(tmp_path):
    calls=[]
    def worker(t,thread,folder,fd):calls.append(thread);emit(folder,GOOD);return 0
    s=m.Supervisor(tmp_path,worker);s.enqueue(task());s.tick()
    t=task('TASK-B');t['parent_task_id']='TASK-A';s.enqueue(t);s.tick()
    assert calls==[None,GOOD[0]['thread_id']]

def test_repository_conflict_duplicate_task_input(tmp_path):
    s=m.Supervisor(tmp_path);s.enqueue(task());t=task();t['priority']=12
    with pytest.raises(m.Blocked,match='CONFLICT'):s.enqueue(t)

def test_environment_recovery_cannot_bypass_usage_pause(tmp_path):
    def worker(t,thread,folder,fd):emit(folder,[{'type':'error','message':'usage_limit_reached'}]);return 1
    s=m.Supervisor(tmp_path,worker);s.enqueue(task());s.tick()
    with pytest.raises(m.Blocked,match='NOT_ENVIRONMENT'):s.recover_environment()

def test_bridge_outage_queue_and_return(tmp_path,monkeypatch):
    clock=[1000];ready=[False];calls=[]
    monkeypatch.setattr(m,'bridge_ready',lambda:ready[0])
    def worker(t,thread,folder,fd):calls.append(1);emit(folder,GOOD);return 0
    s=m.Supervisor(tmp_path,worker,lambda:clock[0]);t=task();t['requires_bridge']=True;s.enqueue(t)
    assert s.tick()['reason']=='BRIDGE_FAILURE';assert calls==[]
    ready[0]=True;clock[0]+=3601
    assert s.tick()['state']=='COMPLETE' and calls==[1]

def test_process_backoff_survives_new_enqueue(tmp_path):
    clock=[1000];calls=[]
    def worker(t,thread,folder,fd):calls.append(t['task_id']);emit(folder,[]);return 1
    s=m.Supervisor(tmp_path,worker,lambda:clock[0]);s.enqueue(task());s.tick();s.enqueue(task('TASK-B',1))
    s.tick('CONSERVE');assert calls==['TASK-A']

def test_missing_database_never_discards_queue(tmp_path):
    s=m.Supervisor(tmp_path);s.enqueue(task());(tmp_path/'runtime.sqlite').unlink()
    with pytest.raises(m.Blocked,match='DATABASE_MISSING'):s.tick()
    assert 'TASK-A' in (tmp_path/'TASK_QUEUE.jsonl').read_text()

def test_critical_never_starts_worker(tmp_path):
    s=m.Supervisor(tmp_path,lambda *a:pytest.fail('CRITICAL must checkpoint not start'));s.enqueue(task())
    assert s.tick('CRITICAL')['reason']=='CRITICAL_NO_NEW_WORK'

def test_installed_provenance_fails_closed(tmp_path):
    with pytest.raises(m.Blocked,match='NOT_PINNED'):m.verify_installation(tmp_path)
    m.atomic(tmp_path/'CONFIG.json',{'supervisor_sha256':'wrong','policy':'CHATGPT_REASONING_ONLY_NO_TOOLS_NO_RESET'})
    with pytest.raises(m.Blocked,match='SOURCE_CHANGED'):m.verify_installation(tmp_path)
