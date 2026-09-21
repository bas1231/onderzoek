from pathlib import Path
from datetime import datetime
import json
R=Path.cwd();S=Path.home()/'.local/state/prediction-research/kalshi_weather_index_manifests';P=json.loads((R/'knowledge/candidates/protocols/KWI-FULL-STATION-PRECANONICAL-24H-V1.json').read_text());cut=datetime.fromisoformat(P['prospective_cutoff']);end=datetime.fromisoformat(P['window_end']);rec=[]
for p in S.glob('*.json'):
 try:d=json.loads(p.read_text());rec.append((datetime.fromisoformat(d['retrieved_at']),d))
 except Exception:pass
rec.sort(key=lambda x:x);inc={};comp={}
for ts,d in rec:
 for r in d.get('cities',[]):
  city=str(r.get('city') or '');cfg=str(r.get('config_version') or '');i=r.get('latest_incomplete') or {};z=r.get('latest_complete') or {}
  if i.get('t') is not None:
   k=(city,cfg,int(i['t']));temps=[float(x['temp_f']) for x in i.get('stations',[]) if isinstance(x,dict) and x.get('temp_f') is not None]
   if k not in inc:inc=(ts,temps,z.get('t'),z.get('v'),z.get('contributors'))
  if z.get('t') is not None and z.get('v') is not None:comp.setdefault((city,cfg,int(z['t'])),(ts,float(z['v'])))
rows=[];nonpos=0
for k,v in inc.items():
 ts,temps,pt,pv,pc=v
 if ts<cut or ts>end or pc is None or len(temps)!=int(pc) or pt is None or pv is None or int(pt)>=k[2] or k not in comp:continue
 ct,av=comp[k];lead=(ct-ts).total_seconds();nonpos+=int(lead<=0);pred=sum(temps)/len(temps);rows.append((k[0],abs(pred-av),abs(float(pv)-av),lead))
print('STRICT_N',len(rows));print('NONPOSITIVE_LEAD',nonpos);print('EXACT_1E9',sum(1 for row in rows if row[1]<1e-9))
for city in ['chicago','miami','nyc']:
 q=[row for row in rows if row[0]==city];print('CITY',city,'N',len(q),'PRIMARY_MAE',sum(row[1] for row in q)/len(q) if q else None,'BASELINE_MAE',sum(row[2] for row in q)/len(q) if q else None)
qual=[]
for city in ['chicago','miami','nyc']:
 if len([row for row in rows if row[0]==city])>=30:qual.append(city)
overall=bool(rows) and sum(row[1] for row in rows)<sum(row[2] for row in rows);percity=all(sum(row[1] for row in rows if row[0]==city)<sum(row[2] for row in rows if row[0]==city) for city in qual)
print('QUALIFIED',len(qual));print('STRICT_SURVIVAL_PASS',overall and percity and len(qual)>=2 and nonpos==0);print('E392R1_REDTEAM_DONE')