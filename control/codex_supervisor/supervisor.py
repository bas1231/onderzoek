"""Duurzame, begrensde Codex reasoning-worker; geen uitvoerende research/tradingtool."""
import contextlib,datetime,fcntl,hashlib,json,os,pathlib,re,signal,sqlite3,subprocess,tempfile,time,uuid
P=pathlib.Path
STATES={'IDLE','RUNNING','PAUSED_USAGE_LIMIT','WAITING_RETRY','BLOCKED','FAILED','COMPLETE'}
class Blocked(RuntimeError):pass

def digest(data):return hashlib.sha256(data).hexdigest()
def atomic(path,data):
    path=P(path);path.parent.mkdir(parents=True,exist_ok=True)
    b=data.encode() if isinstance(data,str) else (json.dumps(data,indent=2,ensure_ascii=False)+'\n').encode()
    fd,name=tempfile.mkstemp(prefix='.atomic-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
        os.replace(name,path)
        fd=os.open(path.parent,os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
    finally:
        if os.path.exists(name):os.unlink(name)

def classify(events,rc):
    thread=None;final=None;completed=False;errors=[]
    for e in events:
        if e.get('type')=='thread.started':thread=e.get('thread_id')
        if e.get('type')=='item.completed' and e.get('item',{}).get('type')=='agent_message':final=e['item'].get('text')
        if e.get('type')=='turn.completed':completed=True
        if e.get('type') in ('error','turn.failed'):errors.append(json.dumps(e).lower())
    text=' '.join(errors)
    if any(s in text for s in ['usage_limit','usage limit','quota_exceeded','you’ve hit your usage limit',"you've hit your usage limit"]):return 'USAGE_LIMIT',thread,final
    if any(s in text for s in ['unauthorized','authentication','api key']):return 'SAFETY_BLOCK',thread,final
    if errors or rc!=0:return 'CODEX_PROCESS_FAILURE',thread,final
    if not completed or not final:return 'TASK_FAILURE',thread,final
    return 'COMPLETE',thread,final

def events_from(path):
    events=[]
    if not path.exists():return events
    for line in path.read_text().splitlines():
        try:e=json.loads(line)
        except ValueError:continue # crash-fragment; zonder turn.completed nooit complete
        if isinstance(e,dict):events.append(e)
    return events

def bridge_ready():
    import http.client
    c=http.client.HTTPConnection('127.0.0.1',8766,timeout=3)
    try:
        token=(P.home()/'.config/prediction-chat-bridge/token').read_text().strip()
        c.request('GET','/health',headers={'Authorization':'Bearer '+token});r=c.getresponse();data=json.loads(r.read(65536))
        return r.status==200 and data.get('ok') is True and 'BRIDGE_PING' in data.get('allowed_actions',[])
    except (OSError,ValueError,http.client.HTTPException):return False
    finally:c.close()

def validate_task(t):
    if not isinstance(t,dict) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',str(t.get('task_id',''))):raise Blocked('MALFORMED_TASK_ID')
    required={'task_id','task_class','priority','expected_value','estimated_reasoning_cost','created_at','prompt','input_sha256'}
    if not required<=t.keys() or t['task_class'] not in ('research_review','infrastructure_review','local_validation'):raise Blocked('MALFORMED_TASK')
    if not isinstance(t['prompt'],str) or not t['prompt'].strip() or len(t['prompt'])>100000:raise Blocked('MALFORMED_PROMPT')
    if digest(t['prompt'].encode())!=t['input_sha256']:raise Blocked('PROVENANCE_MISMATCH')
    for key in ['priority','expected_value','estimated_reasoning_cost']:
        if type(t[key]) not in (int,float) or not 0<=t[key]<1e9:raise Blocked('MALFORMED_PRIORITY')
    if type(t.get('requires_bridge',False)) is not bool:raise Blocked('MALFORMED_BRIDGE_REQUIREMENT')
    if t['estimated_reasoning_cost']<=0:raise Blocked('MALFORMED_COST')
    return t

class Supervisor:
    def __init__(self,root,worker=None,clock=time.time,candidate_source=None):
        self.root=P(root);self.root.mkdir(parents=True,exist_ok=True);self.worker=worker or CodexWorker();self.clock=clock
        self.lock=None;self.db=None;self.candidate_source=candidate_source
    @contextlib.contextmanager
    def locked(self):
        with (self.root/'worker.lock').open('a+') as f:
            try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise Blocked('WORKER_ALREADY_RUNNING')
            self.lock=f
            dbpath=self.root/'runtime.sqlite'
            if (not dbpath.exists() or dbpath.stat().st_size==0) and (self.root/'TASK_QUEUE.jsonl').exists():raise Blocked('DATABASE_MISSING_RECOVERY_REQUIRED')
            self.db=sqlite3.connect(self.root/'runtime.sqlite',timeout=10)
            self.db.execute('pragma journal_mode=WAL');self.db.execute('pragma synchronous=FULL')
            self.db.executescript('CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, body TEXT NOT NULL,status TEXT NOT NULL,attempt INTEGER NOT NULL DEFAULT 0,thread TEXT,run TEXT); CREATE TABLE IF NOT EXISTS transitions(seq INTEGER PRIMARY KEY,state TEXT,task TEXT,reason TEXT,attempt INTEGER,checkpoint TEXT,next_action TEXT,stamp REAL,retry REAL);')
            try:yield
            finally:self.db.close();self.db=None;self.lock=None
    def state(self):
        row=self.db.execute('select state,task,reason,attempt,checkpoint,next_action,stamp,retry from transitions order by seq desc limit 1').fetchone()
        return dict(zip(['state','task_id','reason','attempt','checkpoint','next_action','timestamp','retry_at'],row)) if row else {'state':'IDLE','retry_at':0}
    def transition(self,state,task,reason,attempt,checkpoint='',retry=0):
        if state not in STATES:raise Blocked('INVALID_STATE')
        if reason=='QUEUE_EMPTY':next_action='Wacht op nieuwe eligible input'
        elif reason=='NEEDS_REVISION_REQUIRES_NEW_VERSION_AND_REVIEW':next_action='Nieuwe protocolversie en Director-herbeoordeling vereist'
        elif state=='BLOCKED':next_action='Los de geregistreerde blokkade op; hervat pas na provenancecontrole'
        else:next_action='Hervat dezelfde taak na provenancecontrole' if state!='COMPLETE' else 'Selecteer hoogste prioriteit'
        self.db.execute('insert into transitions(state,task,reason,attempt,checkpoint,next_action,stamp,retry) values(?,?,?,?,?,?,?,?)',(state,task,reason,attempt,checkpoint,next_action,self.clock(),retry))
    def views(self):
        atomic(self.root/'STATE.json',self.state())
        print(json.dumps({'event':'SUPERVISOR_STATE',**self.state()}),flush=True)
        rows=[]
        for body,status,attempt in self.db.execute('select body,status,attempt from tasks order by id'):
            t=json.loads(body);t.update(status=status,attempts=attempt);rows.append(t)
        atomic(self.root/'TASK_QUEUE.jsonl',''.join(json.dumps(t,ensure_ascii=False)+'\n' for t in rows))
    def validate_views(self):
        # Handmatig corrupte view is geen reden om stilzwijgend nieuwe AI-work te starten.
        p=self.root/'STATE.json'
        if p.exists():
            try:v=json.loads(p.read_text())
            except ValueError:raise Blocked('CORRUPT_STATE_VIEW')
            if not isinstance(v,dict) or v.get('state') not in STATES:raise Blocked('CORRUPT_STATE_VIEW')
        continuation=self.root/'CONTINUATION.json'
        if continuation.exists():
            try:
                c=json.loads(continuation.read_text());row=self.db.execute('select body from tasks where id=?',(c['task_id'],)).fetchone()
                if not row or json.loads(row[0])['input_sha256']!=c['input_sha256'] or c['state'] not in STATES or c['next_action'] not in ('resume_same_task','select_next'):raise Blocked('MALFORMED_CONTINUATION')
            except (ValueError,KeyError,TypeError):raise Blocked('MALFORMED_CONTINUATION')
        q=self.root/'TASK_QUEUE.jsonl'
        if q.exists():
            try:
                for line in q.read_text().splitlines():validate_task(json.loads(line))
            except (ValueError,KeyError,TypeError):raise Blocked('CORRUPT_QUEUE_VIEW')
    def enqueue(self,t):
        validate_task(t)
        with self.locked():
            self.validate_views();old=self.db.execute('select body from tasks where id=?',(t['task_id'],)).fetchone();body=json.dumps(t,sort_keys=True)
            if old and old[0]!=body:raise Blocked('DUPLICATE_TASK_CONFLICT')
            parent_thread=None
            if t.get('parent_task_id'):
                parent=self.db.execute('select status,thread from tasks where id=?',(t['parent_task_id'],)).fetchone()
                if not parent or parent[0]!='COMPLETE' or not parent[1]:raise Blocked('PARENT_NOT_COMPLETE')
                parent_thread=parent[1]
            with self.db:
                self.db.execute('insert or ignore into tasks(id,body,status,thread) values(?,?,?,?)',(t['task_id'],body,'QUEUED',parent_thread))
                quota=self.db.execute("select max(retry) from transitions where reason='USAGE_LIMIT'").fetchone()[0] or 0
                if not old and quota<=self.clock():self.transition('IDLE',t['task_id'],'QUEUED',0)
            self.views()
    def finish(self,t,attempt,folder,rc):
        events=events_from(folder/'events.jsonl')
        category,thread,final=classify(events,rc)
        err=folder/'stderr.log'
        if not events and err.exists() and 'Read-only file system' in err.read_text():category='ENVIRONMENT_FAILURE'
        if category=='COMPLETE' and t.get('candidate_dispatch'):
            try:
                import candidate_dispatch
                result=candidate_dispatch.validate_result(t,final)
                completion_hash=digest(final.encode())
                overlay,record,already=candidate_dispatch.apply_candidate_result(self,t,result,completion_hash,self.clock())
                atomic(folder/'CANDIDATE_APPLIED.json',{'task_id':t['task_id'],'input_sha256':t['input_sha256'],'completion_hash':completion_hash,'overlay_ref':str(overlay.relative_to(self.root)),'queue_status':record['queue_status'],'already_applied':already,'owner_source_mutated':False})
                print(json.dumps({'event':'RESULT_APPLIED_NEXT_ACTION_RECORDED','task_id':t['task_id'],'candidate_id':t['candidate_id'],'queue_status':record['queue_status']}),flush=True)
            except (ValueError,OSError,KeyError) as exc:
                atomic(folder/'CANDIDATE_REJECTED.json',{'reason':str(exc)});category='TASK_FAILURE'
        if category=='COMPLETE':
            completion={'task_id':t['task_id'],'input_sha256':t['input_sha256'],'attempt':attempt,'thread_id':thread,'final':final,'timestamp':self.clock()}
            atomic(folder/'COMPLETE.json',completion)
        self.apply_result(t,attempt,folder,category,thread)
    def apply_result(self,t,attempt,folder,category,thread):
        state={'COMPLETE':'COMPLETE','USAGE_LIMIT':'PAUSED_USAGE_LIMIT','SAFETY_BLOCK':'BLOCKED','CODEX_PROCESS_FAILURE':'WAITING_RETRY','TASK_FAILURE':'FAILED','ENVIRONMENT_FAILURE':'WAITING_RETRY','BRIDGE_FAILURE':'WAITING_RETRY','REPOSITORY_CONFLICT':'BLOCKED'}.get(category,'BLOCKED')
        if state=='WAITING_RETRY' and attempt>=3:state='FAILED'
        retry=self.clock()+(18000 if category=='USAGE_LIMIT' else 3600) if state in ('PAUSED_USAGE_LIMIT','WAITING_RETRY') else 0
        with self.db:
            self.db.execute('update tasks set status=?,thread=coalesce(?,thread) where id=?',(state,thread,t['task_id']))
            self.transition(state,t['task_id'],category,attempt,str(folder.relative_to(self.root)),retry)
        atomic(self.root/'CONTINUATION.json',{'task_id':t['task_id'],'input_sha256':t['input_sha256'],'state':state,'checkpoint':str(folder.relative_to(self.root)),'next_action':'resume_same_task' if state!='COMPLETE' else 'select_next'})
        atomic(self.root/'CONTINUATION.md',f"# Hervatting\n\nTaak: {t['task_id']}\nStatus: {state}\nReden: {category}\nInputsha: {t['input_sha256']}\nCheckpoint: {folder.name}\nVolgende stap: dezelfde onveranderde taak hervatten na retry_at; geen resets, push, API keys of tools.\n")
        self.views()
    def execute_validation(self,t,attempt,folder):
        try:
            import candidate_validation,candidate_dispatch
            t['run_path']=str(folder.relative_to(self.root))
            report=candidate_validation.run(t,P(__file__).resolve().parents[2],folder)
            overlay,state=candidate_dispatch.apply_validation(self,t,report)
            atomic(folder/'COMPLETE.json',{'task_id':t['task_id'],'input_sha256':t['input_sha256'],'attempt':attempt,'validation_hash':report['runs'][0]['result']['protocol_id'],'timestamp':self.clock()})
            with self.db:
                self.db.execute('update tasks set status=? where id=?',('COMPLETE',t['task_id']))
                self.transition('COMPLETE',t['task_id'],'VALIDATION_COMPLETE',attempt,str(folder.relative_to(self.root)))
            atomic(self.root/'CONTINUATION.json',{'task_id':t['task_id'],'input_sha256':t['input_sha256'],'state':'COMPLETE','checkpoint':str(folder.relative_to(self.root)),'next_action':'candidate_validation'})
            self.views();print(json.dumps({'event':'CANDIDATE_VALIDATION_COMPLETE','candidate_id':t['candidate_id'],'activation_authorized':False}),flush=True)
        except Exception as exc:
            atomic(folder/'VALIDATION_FAILURE.json',{'type':type(exc).__name__,'reason':str(exc)})
            with self.db:
                self.db.execute('update tasks set status=? where id=?',('FAILED',t['task_id']))
                self.transition('FAILED',t['task_id'],'VALIDATION_FAILURE',attempt,str(folder.relative_to(self.root)))
            self.views();print(json.dumps({'event':'QUEUE_BLOCKED','candidate_id':t.get('candidate_id'),'reason':'VALIDATION_FAILURE'}),flush=True)
    def recover_environment(self):
        with self.locked():
            self.validate_views();state=self.state()
            if state.get('state')!='WAITING_RETRY':raise Blocked('NOT_ENVIRONMENT_RETRY')
            folder=self.root/state['checkpoint'];err=folder/'stderr.log'
            if events_from(folder/'events.jsonl') or not err.exists() or 'Read-only file system' not in err.read_text():raise Blocked('NOT_PREINVOCATION_ENVIRONMENT_FAILURE')
            with self.db:self.transition('WAITING_RETRY',state['task_id'],'ENVIRONMENT_RETRY_AUTHORIZED',state['attempt'],state['checkpoint'],0)
            self.views()
    def tick(self,mode='NORMAL'):
        if mode not in ('NORMAL','CONSERVE','CRITICAL'):raise Blocked('INVALID_BUDGET_MODE')
        with self.locked():
            self.validate_views()
            # Recover immutable completion first, before considering any new invocation.
            pending=self.db.execute("select id,body,attempt,thread,run from tasks where status='RUNNING'").fetchall()
            for tid,body,attempt,thread,runpath in pending:
                t=validate_task(json.loads(body));folder=self.root/runpath;complete=folder/'COMPLETE.json'
                if complete.exists():
                    c=json.loads(complete.read_text())
                    if c.get('task_id')!=tid or c.get('input_sha256')!=t['input_sha256']:raise Blocked('CORRUPT_COMPLETION')
                    self.apply_result(t,attempt,folder,'COMPLETE',c.get('thread_id'))
                elif t.get('candidate_validation'):
                    self.execute_validation(t,attempt,folder)
                else:
                    events=events_from(folder/'events.jsonl');rc=0 if any(e.get('type')=='turn.completed' for e in events) else -1
                    self.finish(t,attempt,folder,rc)
            state=self.state()
            quota=self.db.execute("select max(retry) from transitions where reason='USAGE_LIMIT'").fetchone()[0] or 0
            if quota>self.clock():return {'state':'PAUSED_USAGE_LIMIT','retry_at':quota}
            if state.get('retry_at',0)>self.clock():return state
            if mode=='CRITICAL':return {'state':'IDLE','reason':'CRITICAL_NO_NEW_WORK'}
            rows=self.db.execute("select body,attempt,thread,status from tasks where status in ('QUEUED','PAUSED_USAGE_LIMIT','WAITING_RETRY')").fetchall()
            if not rows and self.candidate_source:
                candidate=self.candidate_source(self)
                if candidate and candidate.get('queue_blocked'):
                    reason=candidate['reason'];state=self.state()
                    next_action='Nieuwe protocolversie en Director-herbeoordeling vereist' if reason=='NEEDS_REVISION_REQUIRES_NEW_VERSION_AND_REVIEW' else 'Los de geregistreerde blokkade op; hervat pas na provenancecontrole'
                    if state.get('state')!='BLOCKED' or state.get('reason')!=reason or state.get('next_action')!=next_action:
                        with self.db:self.transition('BLOCKED',candidate.get('candidate_id',''),reason,0)
                        self.views()
                    print(json.dumps({'event':'QUEUE_BLOCKED','candidate_id':candidate.get('candidate_id'),'reason':reason}),flush=True)
                    return {**self.state(),'state':'BLOCKED','reason':reason}
                if candidate:
                    validate_task(candidate)
                    with self.db:
                        self.db.execute('insert into tasks(id,body,status) values(?,?,?)',(candidate['task_id'],json.dumps(candidate,sort_keys=True),'QUEUED'))
                        self.transition('IDLE',candidate['task_id'],'TASK_QUEUED',0)
                    self.views()
                    rows=[(json.dumps(candidate),0,None,'QUEUED')]
            if not rows:
                with self.db:self.transition('IDLE','','QUEUE_EMPTY',0)
                self.views();return self.state()
            choices=[(validate_task(json.loads(b)),a,th,st) for b,a,th,st in rows]
            choices=[x for x in choices if (self.db.execute('select retry from transitions where task=? order by seq desc limit 1',(x[0]['task_id'],)).fetchone() or (0,))[0]<=self.clock()]
            if mode=='CONSERVE':choices=[x for x in choices if x[0]['priority']>=80]
            if not choices:return {'state':'IDLE','reason':'CONSERVE_NO_HIGH_VALUE_WORK'}
            t,attempt,thread,st=max(choices,key=lambda x:(x[0]['priority'],x[0]['expected_value']/x[0]['estimated_reasoning_cost']))
            if t.get('requires_bridge') and not bridge_ready():
                with self.db:
                    self.db.execute('update tasks set status=? where id=?',('WAITING_RETRY',t['task_id']))
                    self.transition('WAITING_RETRY',t['task_id'],'BRIDGE_FAILURE',attempt,retry=self.clock()+3600)
                self.views();return self.state()
            attempt+=1
            folder=self.root/'runs'/f"{t['task_id']}-{attempt}-{uuid.uuid4().hex[:8]}";folder.mkdir(parents=True)
            atomic(folder/'TASK.json',t)
            with self.db:
                self.db.execute('update tasks set status=?,attempt=?,run=? where id=?',('RUNNING',attempt,str(folder.relative_to(self.root)),t['task_id']))
                self.transition('RUNNING',t['task_id'],'WORKER_START',attempt,str(folder.relative_to(self.root)))
            self.views()
            atomic(self.root/'ACTIVE_GOAL.md',f"# Actieve taak\n\n{t['task_id']}\n\n{t['prompt']}\n")
            if t.get('candidate_validation'):
                self.execute_validation(t,attempt,folder);return self.state()
            try:rc=self.worker(t,thread,folder,self.lock.fileno())
            except Blocked as exc:
                atomic(folder/'worker_error.json',{'type':type(exc).__name__,'reason':str(exc)})
                self.apply_result(t,attempt,folder,'SAFETY_BLOCK',thread)
                return self.state()
            except Exception as exc:
                atomic(folder/'worker_error.json',{'type':type(exc).__name__});rc=-1
            self.finish(t,attempt,folder,rc)
            return self.state()

class CodexWorker:
    def __init__(self,binary=None):
        self.binary=binary or str(P.home()/'.local/npm/bin/codex')
    def __call__(self,task,thread,folder,lock_fd):
        env={k:os.environ[k] for k in ['HOME','PATH','LANG','SSL_CERT_FILE'] if k in os.environ}
        auth=subprocess.run([self.binary,'login','status'],capture_output=True,text=True,env=env,timeout=20)
        if auth.returncode or 'Logged in using ChatGPT' not in auth.stdout+auth.stderr:raise Blocked('CHATGPT_INCLUDED_AUTH_REQUIRED')
        cache=json.loads((P.home()/'.codex/models_cache.json').read_text());models=[m for m in cache.get('models',[]) if m.get('visibility')=='list']
        if not models:raise Blocked('AVAILABLE_MODEL_UNKNOWN')
        model=min(models,key=lambda m:m.get('priority',999))['slug']
        args=[self.binary,'exec']+(['resume',thread] if thread else [])+['--json','--ignore-user-config','--ignore-rules','--skip-git-repo-check','-m',model,'-c','sandbox_mode="read-only"','-c','approval_policy="never"','-c','web_search="disabled"','-c','model_reasoning_effort="high"','--disable','shell_tool','--disable','unified_exec','--disable','apps','--disable','apply_patch_freeform','-']
        # Geen shell, hooks, repo-config, MCP of writable eigenaarworkspace beschikbaar.
        prompt='Reason only over the supplied input. Do not call tools, spend money, use credentials, alter files, activate resets, or execute commands. Give a falsifiable research/review conclusion; NO_PROVEN_EDGE is valid.\nTask ID: '+task['task_id']+'\n'+task['prompt']
        with tempfile.TemporaryDirectory(prefix='prediction-codex-reasoning-') as cwd:
            with os.fdopen(os.open(folder/'events.jsonl',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_DSYNC,0o600),'w') as output,(folder/'stderr.log').open('w') as err:
                proc=subprocess.Popen(args,cwd=cwd,env=env,stdin=subprocess.PIPE,stdout=output,stderr=err,text=True,start_new_session=True,pass_fds=(lock_fd,))
                atomic(folder/'WORKER.json',{'pid':proc.pid,'model':model,'thread_id':thread,'started_at':time.time(),'command_flags':args[1:-1]})
                try:proc.communicate(prompt,timeout=1800)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGTERM);proc.wait(timeout=15);return -1
                output.flush();os.fsync(output.fileno())
                return proc.returncode

def verify_installation(root):
    config=root/'CONFIG.json'
    if not config.exists():raise Blocked('SUPERVISOR_INSTALLATION_NOT_PINNED')
    data=json.loads(config.read_text())
    if data.get('supervisor_sha256')!=digest(P(__file__).read_bytes()):raise Blocked('SUPERVISOR_SOURCE_CHANGED')
    if data.get('policy')!='CHATGPT_REASONING_ONLY_NO_TOOLS_NO_RESET':raise Blocked('SUPERVISOR_POLICY_CHANGED')
    policy=P(__file__).resolve().parents[1]/'hourly/candidate_queue.py'
    if data.get('candidate_policy_sha256')!=digest(policy.read_bytes()):raise Blocked('CANDIDATE_POLICY_SOURCE_CHANGED')
    for name in ('candidate_dispatch.py',):
        if data.get(name+'_sha256')!=digest(P(__file__).with_name(name).read_bytes()):raise Blocked('CANDIDATE_DISPATCH_SOURCE_CHANGED')

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('action',choices=['tick','enqueue','status','recover-environment']);p.add_argument('--root',type=P,default=P(__file__).resolve().parents[2]/'knowledge/codex_runtime');p.add_argument('--task',type=P);p.add_argument('--mode',default='NORMAL');a=p.parse_args();s=Supervisor(a.root)
    try:
        verify_installation(a.root)
        if a.action=='enqueue':s.enqueue(json.loads(a.task.read_text()));print('QUEUED')
        elif a.action=='recover-environment':s.recover_environment();print('ENVIRONMENT_RETRY_READY')
        elif a.action=='tick':
            import candidate_dispatch
            s.candidate_source=lambda current:candidate_dispatch.select_next(current,P(__file__).resolve().parents[2])
            print(json.dumps(s.tick(a.mode)))
        else:
            with s.locked():print(json.dumps(s.state()))
    except (Blocked,sqlite3.DatabaseError,ValueError) as e:
        if str(e)=='WORKER_ALREADY_RUNNING':print('WORKER_ALREADY_RUNNING');return 75
        atomic(a.root/'BLOCKER.json',{'state':'BLOCKED','reason':str(e),'timestamp':time.time()});print('BLOCKED:',e);return 2
    return 0
if __name__=='__main__':raise SystemExit(main())
