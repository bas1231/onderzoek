from pathlib import Path
import json
ROOT=Path.cwd()
ids=['SOURCE-QUALITY-E115','SEMANTIC-QUALITY-FILTER-E116','DELAY-CHECK-E117','EXTENSION-WATCHDOG-AUDIT-E118','POST-RESET-CANARY-E119','RECONCILE-DELAYED-E121']
out={}
for tid in ids:
 hits=[]
 for base in [ROOT/'control/tasks',ROOT/'control/results',ROOT/'control/lifecycle']:
  if not base.exists(): continue
  for p in base.rglob('*'):
   if tid not in p.name: continue
   item={'path':str(p.relative_to(ROOT))}
   if p.is_file() and p.suffix=='.json':
    try:
     d=json.loads(p.read_text())
     item['status']=d.get('status') or d.get('state')
     item['history']=d.get('history')
    except Exception as e:
     item['read_error']=type(e).name
   hits.append(item)
 out[tid]=hits
print(json.dumps(out,indent=2,default=str))