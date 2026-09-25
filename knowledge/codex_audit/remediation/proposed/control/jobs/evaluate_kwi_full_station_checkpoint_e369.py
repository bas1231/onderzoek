from pathlib import Path
from datetime import datetime,timezone
import json
import math

root=Path.cwd()
home=Path.home()
state=home/'.local/state/prediction-research'
manifests=state/'kalshi_weather_index_manifests'
protocol_path=root/'knowledge/candidates/protocols/KWI-FULL-STATION-PRECANONICAL-24H-V1.json'
if not manifests.exists():
    raise SystemExit('manifest_dir_missing')
if not protocol_path.exists():
    raise SystemExit('protocol_missing')
protocol=json.loads(protocol_path.read_text(encoding='utf-8'))
cutoff=datetime.fromisoformat(str(protocol.get('prospective_cutoff')))
window_end=datetime.fromisoformat(str(protocol.get('window_end')))

files=[p for p in manifests.iterdir() if p.is_file() and p.suffix=='.json']
records=list()
for p in files:
    try:
        data=json.loads(p.read_text(encoding='utf-8'))
        retrieved=datetime.fromisoformat(str(data.get('retrieved_at')))
    except Exception:
        continue
    if data.get('timestamp_semantics') != 'response_body_received':
        continue
    records.append((retrieved,p,data))
records.sort(key=lambda item:item)

first_seen=dict()
first_complete=dict()
for retrieved,p,data in records:
    cities=data.get('cities') or tuple()
    if not isinstance(cities,list):
        continue
    for cityrow in cities:
        if not isinstance(cityrow,dict):
            continue
        city=str(cityrow.get('city') or '')
        config=str(cityrow.get('config_version') or '')
        if not config:
            continue
        try:
            city_received=datetime.fromisoformat(str(cityrow.get('retrieved_at',data.get('retrieved_at'))))
        except (ValueError, TypeError):
            continue
        incomplete=cityrow.get('latest_incomplete') or dict()
        if isinstance(incomplete,dict) and incomplete.get('t') is not None:
            try:
                target_t=int(incomplete.get('t'))
            except Exception:
                target_t=None
            if target_t is not None:
                key=city+'|'+config+'|'+str(target_t)
                if key not in first_seen:
                    stations=incomplete.get('stations') or tuple()
                    temps=list()
                    for station in stations:
                        if not isinstance(station,dict):
                            continue
                        try:
                            temps.append(float(station.get('temp_f')))
                        except Exception:
                            continue
                    previous=cityrow.get('latest_complete') or dict()
                    previous_t=None
                    previous_v=None
                    previous_contributors=None
                    if isinstance(previous,dict):
                        try:
                            previous_t=int(previous.get('t'))
                            previous_v=float(previous.get('v'))
                            previous_contributors=int(previous.get('contributors'))
                        except Exception:
                            previous_t=None
                            previous_v=None
                            previous_contributors=None
                    first_seen[key]=dict(city=city,config_version=config,t=target_t,first_incomplete_at=city_received.isoformat(),first_incomplete_epoch=city_received.timestamp(),station_count=len(temps),station_mean=(sum(temps)/len(temps) if temps else None),previous_t=previous_t,previous_v=previous_v,previous_contributors=previous_contributors,manifest=p.name)
        complete=cityrow.get('latest_complete') or dict()
        if isinstance(complete,dict) and complete.get('t') is not None and complete.get('v') is not None:
            try:
                complete_t=int(complete.get('t'))
                complete_v=float(complete.get('v'))
            except Exception:
                complete_t=None
                complete_v=None
            if complete_t is not None and complete_v is not None:
                key=city+'|'+config+'|'+str(complete_t)
                if key not in first_complete:
                    first_complete[key]=dict(target_v=complete_v,first_complete_at=city_received.isoformat(),first_complete_epoch=city_received.timestamp())

eligible=list()
open_pairs=list()
excluded_pre_cutoff=0
excluded_station_count=0
excluded_missing_baseline=0
for key in sorted(first_seen):
    row=first_seen.get(key) or dict()
    try:
        first_dt=datetime.fromisoformat(str(row.get('first_incomplete_at')))
    except Exception:
        continue
    if first_dt<cutoff:
        excluded_pre_cutoff+=1
        continue
    if first_dt>window_end:
        continue
    station_count=row.get('station_count')
    expected=row.get('previous_contributors')
    if expected is None or station_count!=expected:
        excluded_station_count+=1
        continue
    previous_t=row.get('previous_t')
    previous_v=row.get('previous_v')
    if previous_t is None or previous_v is None or int(previous_t)>=int(row.get('t')):
        excluded_missing_baseline+=1
        continue
    if row.get('station_mean') is None:
        excluded_missing_baseline+=1
        continue
    target=first_complete.get(key)
    if not isinstance(target,dict):
        open_pairs.append(row)
        continue
    if float(target['first_complete_epoch']) <= float(row['first_incomplete_epoch']):
        continue
    primary=float(row.get('station_mean'))
    baseline=float(previous_v)
    actual=float(target.get('target_v'))
    lead=float(target.get('first_complete_epoch'))-float(row.get('first_incomplete_epoch'))
    scored=dict(row)
    scored['target_v']=actual
    scored['first_complete_at']=target.get('first_complete_at')
    scored['lead_seconds_to_first_complete']=lead
    scored['primary_error']=primary-actual
    scored['baseline_error']=baseline-actual
    scored['primary_abs_error']=abs(primary-actual)
    scored['baseline_abs_error']=abs(baseline-actual)
    eligible.append(scored)

def metrics(rows):
    n=len(rows)
    if n==0:
        return dict(n=0)
    pa=[float(row.get('primary_abs_error')) for row in rows]
    ba=[float(row.get('baseline_abs_error')) for row in rows]
    pe=[float(row.get('primary_error')) for row in rows]
    be=[float(row.get('baseline_error')) for row in rows]
    leads=[float(row.get('lead_seconds_to_first_complete')) for row in rows]
    return dict(n=n,primary_mae=sum(pa)/n,baseline_mae=sum(ba)/n,primary_rmse=math.sqrt(sum(pow(v,2) for v in pe)/n),baseline_rmse=math.sqrt(sum(pow(v,2) for v in be)/n),primary_mean_signed_error=sum(pe)/n,baseline_mean_signed_error=sum(be)/n,lead_seconds_mean=sum(leads)/n,lead_seconds_min=min(leads),lead_seconds_max=max(leads))

overall=metrics(eligible)
by_city=dict()
qualified_cities=0
all_qualified_win=True
for city in ['chicago','miami','nyc']:
    subset=[row for row in eligible if row.get('city')==city]
    item=metrics(subset)
    by_city[city]=item
    if int(item.get('n',0))>=int(protocol.get('minimum_eligible_pairs_per_city')):
        qualified_cities+=1
        if not float(item.get('primary_mae'))<float(item.get('baseline_mae')):
            all_qualified_win=False

min_cities=int(protocol.get('minimum_eligible_cities'))
window_finished=datetime.now(timezone.utc)>=window_end
survival_evaluable=window_finished and qualified_cities>=min_cities
survival_pass=None
if survival_evaluable:
    overall_win=float(overall.get('primary_mae'))<float(overall.get('baseline_mae')) if overall.get('n',0)>0 else False
    survival_pass=bool(overall_win and all_qualified_win)

print('PROTOCOL_ID',protocol.get('protocol_id'))
print('CUTOFF',cutoff.isoformat())
print('WINDOW_END',window_end.isoformat())
print('MANIFEST_COUNT',len(records))
print('SCORABLE_PROSPECTIVE_PAIRS',len(eligible))
print('OPEN_ELIGIBLE_PAIRS',len(open_pairs))
print('EXCLUDED_PRE_CUTOFF',excluded_pre_cutoff)
print('EXCLUDED_STATION_COUNT',excluded_station_count)
print('EXCLUDED_MISSING_BASELINE',excluded_missing_baseline)
print('OVERALL_N',overall.get('n'))
print('OVERALL_PRIMARY_MAE',overall.get('primary_mae'))
print('OVERALL_BASELINE_MAE',overall.get('baseline_mae'))
print('OVERALL_PRIMARY_RMSE',overall.get('primary_rmse'))
print('OVERALL_BASELINE_RMSE',overall.get('baseline_rmse'))
for city in ['chicago','miami','nyc']:
    item=by_city.get(city) or dict()
    print('CITY',city,'N',item.get('n'),'PRIMARY_MAE',item.get('primary_mae'),'BASELINE_MAE',item.get('baseline_mae'),'LEAD_MEAN',item.get('lead_seconds_mean'))
print('QUALIFIED_CITY_COUNT',qualified_cities)
print('WINDOW_FINISHED',window_finished)
print('SURVIVAL_EVALUABLE',survival_evaluable)
print('SURVIVAL_PASS',survival_pass)
print('INTERPRETATION','PROSPECTIVE_CHECKPOINT_ONLY_NO_MARKET_EDGE_NO_PHASE_PROMOTION')

outdir=state/'analysis/kwi_full_station_checkpoints'
outdir.mkdir(parents=True,exist_ok=True)
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out=outdir/(stamp+'-kwi-full-station-checkpoint.json')
payload=dict(generated_at=datetime.now(timezone.utc).isoformat(),protocol_id=protocol.get('protocol_id'),cutoff=cutoff.isoformat(),window_end=window_end.isoformat(),manifest_count=len(records),scorable_prospective_pairs=len(eligible),open_eligible_pairs=len(open_pairs),excluded_pre_cutoff=excluded_pre_cutoff,excluded_station_count=excluded_station_count,excluded_missing_baseline=excluded_missing_baseline,overall=overall,by_city=by_city,qualified_city_count=qualified_cities,window_finished=window_finished,survival_evaluable=survival_evaluable,survival_pass=survival_pass,rows=eligible,open_pairs=open_pairs)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')
print('PATH',out)
print('KWI_FULL_STATION_CHECKPOINT_PASS')
