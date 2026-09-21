from pathlib import Path
from datetime import datetime
import json
root=Path.cwd()
state=Path.home()/'.local/state/prediction-research/kalshi_weather_index_manifests'
protocol=json.loads((root/'knowledge/candidates/protocols/KWI-FULL-STATION-PRECANONICAL-24H-V1.json').read_text())
cut=datetime.fromisoformat(protocol.get('prospective_cutoff'))
end=datetime.fromisoformat(protocol.get('window_end'))
records=[]
for path in state.glob('*.json'):
 try:
  data=json.loads(path.read_text())
  ts=datetime.fromisoformat(data.get('retrieved_at'))
 except Exception:
  continue
 records.append((ts,data))
records.sort()
first_incomplete={}
first_complete={}
for ts,data in records:
 for cityrow in data.get('cities') or ():
  city=str(cityrow.get('city') or '')
  cfg=str(cityrow.get('config_version') or '')
  incomplete=cityrow.get('latest_incomplete') or {}
  complete=cityrow.get('latest_complete') or {}
  incomplete_t=incomplete.get('t')
  if incomplete_t is not None:
   key=(city,cfg,int(incomplete_t))
   temps=[]
   for station in incomplete.get('stations') or ():
    if not isinstance(station,dict):
     continue
    value=station.get('temp_f')
    if value is not None:
     temps.append(float(value))
   first_incomplete.setdefault(key,(ts,tuple(temps),complete.get('t'),complete.get('v'),complete.get('contributors')))
  complete_t=complete.get('t')
  complete_v=complete.get('v')
  if complete_t is not None and complete_v is not None:
   key=(city,cfg,int(complete_t))
   first_complete.setdefault(key,(ts,float(complete_v)))
rows=[]
nonpositive=0
for key,value in first_incomplete.items():
 city,cfg,target_t=key
 ts,temps,previous_t,previous_v,previous_contributors=value
 if ts<cut or ts>end:
  continue
 if previous_contributors is None or len(temps)!=int(previous_contributors):
  continue
 if previous_t is None or previous_v is None or int(previous_t)>=target_t or not temps:
  continue
 target=first_complete.get(key)
 if target is None:
  continue
 target_ts,actual=target
 lead=(target_ts-ts).total_seconds()
 if lead<=0:
  nonpositive+=1
 prediction=sum(temps)/len(temps)
 rows.append((city,abs(prediction-actual),abs(float(previous_v)-actual),lead))
exact=0
primary_total=0.0
baseline_total=0.0
for row in rows:
 city,primary_error,baseline_error,lead=row
 primary_total+=primary_error
 baseline_total+=baseline_error
 if primary_error<1e-9:
  exact+=1
print('STRICT_N',len(rows))
print('NONPOSITIVE_LEAD',nonpositive)
print('EXACT_1E9',exact)
qualified=0
all_qualified_win=True
for wanted in ('chicago','miami','nyc'):
 count=0
 primary_sum=0.0
 baseline_sum=0.0
 lead_sum=0.0
 for row in rows:
  city,primary_error,baseline_error,lead=row
  if city!=wanted:
   continue
  count+=1
  primary_sum+=primary_error
  baseline_sum+=baseline_error
  lead_sum+=lead
 primary_mae=primary_sum/count if count else None
 baseline_mae=baseline_sum/count if count else None
 lead_mean=lead_sum/count if count else None
 print('CITY',wanted,'N',count,'PRIMARY_MAE',primary_mae,'BASELINE_MAE',baseline_mae,'LEAD_MEAN',lead_mean)
 if count>=30:
  qualified+=1
  if not primary_mae<baseline_mae:
   all_qualified_win=False
overall_win=bool(rows) and primary_total<baseline_total
strict_pass=overall_win and all_qualified_win and qualified>=2 and nonpositive==0
print('QUALIFIED_CITY_COUNT',qualified)
print('STRICT_PRIMARY_MAE',primary_total/len(rows) if rows else None)
print('STRICT_BASELINE_MAE',baseline_total/len(rows) if rows else None)
print('STRICT_SURVIVAL_PASS',strict_pass)
print('E392R2_REDTEAM_DONE')