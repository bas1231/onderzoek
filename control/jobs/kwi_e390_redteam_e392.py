from pathlib import Path
from datetime import datetime
import json,math
R=Path.cwd(); S=Path.home()/'.local/state/prediction-research/kalshi_weather_index_manifests'; P=json.loads((R/'knowledge/candidates/protocols/KWI-FULL-STATION-PRECANONICAL-24H-V1.json').read_text()); c=datetime.fromisoformat(P['prospective_cutoff']); w=datetime.fromisoformat(P['window_end']); rec=[]
for p in S.glob('*.json'):
 try:d=json.loads(p.read_text()); rec.append((datetime.fromisoformat(d['retrieved_at']),d))
 except:pass
rec.sort(key=lambda x:x); inc={}; comp={}
for ts,d in rec:
 for r in d.get('cities',[]):
  city=str(r.get('city') or ''); cfg=str(r.get('config_version') or ''); i=r.get('latest_incomplete') or {}; z=r.get('latest_complete') or {}
  if i.get('t') is not None:
   k=(city,cfg,int(i['t'])); temps=[float(x['temp_f']) for x in i.get('stations',[]) if isinstance(x,dict) and x.get('temp_f') is not None]
   if k not in inc:
    pv=z.get('v'); pt=z.get('t'); pc=z.get('contributors'); inc[k]=(ts,temps,pt,pv,pc)
  if z.get('t') is not None and z.get('v') is not None:
   comp.setdefault((city,cfg,int(z['t'])),(ts,float(z['v'])))
rows=[]; nonpos=0
for k,(ts,temps,pt,pv,pc) in inc.items():
 if ts<c or ts>w or pc is None or len(temps)!=int(pc) or pt is None or pv is None or int(pt)>=k[2] or k not in comp:continue
 ct,av=comp[k]; lead=(ct-ts).total_seconds(); nonpos+=lead<=0; pred=sum(temps)/len(temps); rows.append((k[0],abs(pred-av),abs(float(pv)-av),lead))
print('STRICT_N',len(rows)); print('NONPOSITIVE_LEAD',nonpos); print('EXACT_1E9',sum(e<1e-9 for ,e,,_ in rows));
for city in ['chicago','miami','nyc']:
 q=[x for x in rows if x[0]==city]; print('CITY',city,'N',len(q),'PRIMARY_MAE',sum(x[1] for x in q)/len(q) if q else None,'BASELINE_MAE',sum(x[2] for x in q)/len(q) if q else None)
qual=[city for city in ['chicago','miami','nyc'] if len([x for x in rows if x[0]==city])>=30]; overall=bool(rows) and sum(x[1] for x in rows)<sum(x[2] for x in rows); per=all(sum(x[1] for x in rows if x[0]==city)<sum(x[2] for x in rows if x[0]==city) for city in qual); print('QUALIFIED',len(qual)); print('STRICT_SURVIVAL_PASS',overall and per and len(qual)>=2 and nonpos==0); print('E392_REDTEAM_DONE')