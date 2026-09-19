from pathlib import Path
import json,sys,time,tempfile,os
ROOT=Path.cwd(); DIR=ROOT/'control/lifecycle'; DIR.mkdir(parents=True,exist_ok=True)
STATES={'DISCOVERED','ACCEPTED','RUNNING','COMPLETED','FAILED','DELIVERED','ACKED','INCIDENT'}
def p(t): return DIR/(t+'.json')
def load(t):
 f=p(t)
 return json.loads(f.read_text()) if f.exists() else {'task_id':t,'created_at':time.time(),'history':[]}
def update(t,s,detail=''):
 if s not in STATES: raise ValueError('invalid state')
 r=load(t); now=time.time(); r['state']=s; r['updated_at']=now; r['history'].append({'state':s,'at':now,'detail':detail})
 fd,tmp=tempfile.mkstemp(prefix='.'+t+'.',suffix='.tmp',dir=DIR)
 with os.fdopen(fd,'w') as h: json.dump(r,h,indent=2,sort_keys=True); h.write('
'); h.flush(); os.fsync(h.fileno())
 os.replace(tmp,p(t)); return r
if name=='main':
 if len(sys.argv)==2 and sys.argv[1]=='--self-test':
  t='LEDGER_SELFTEST'; a=update(t,'DISCOVERED','self-test'); b=update(t,'ACCEPTED','self-test'); p(t).unlink(missing_ok=True); print(json.dumps({'status':'ok','history':len(b['history']),'final':b}))
 elif len(sys.argv)>=3: print(json.dumps(update(sys.argv[1],sys.argv[2],sys.argv[3] if len(sys.argv)>3 else '')))
 else: print(json.dumps({'status':'ready'}))
