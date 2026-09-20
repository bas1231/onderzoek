from pathlib import Path
from datetime import datetime,timezone
import json
import math

home=Path.home()
state=home/'.local/state/prediction-research'
manifests=state/'kalshi_weather_index_manifests'
protocol_path=Path.cwd()/'knowledge/candidates/protocols/KWI-INCOMPLETE-SIGNAL-FEASIBILITY-V1.json'
if not manifests.exists():
    raise SystemExit('manifest_dir_missing')
if not protocol_path.exists():
    raise SystemExit('protocol_missing')
protocol=json.loads(protocol_path.read_text(encoding='utf-8'))

files=[p for p in manifests.iterdir() if p.is_file() and p.suffix=='.json']
files.sort(key=lambda p:p.stat().st_mtime)
first_incomplete=dict()
targets=dict()
complete_values=dict()

for p in files:
    try:
        data=json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        continue
    retrieved=str(data.get('retrieved_at') or '')
    cities=data.get('cities') or tuple()
    if not isinstance(cities,list):
        continue
    for cityrow in cities:
        if not isinstance(cityrow,dict):
            continue
        city=str(cityrow.get('city') or '')
        incomplete=cityrow.get('latest_incomplete') or dict()
        previous=cityrow.get('latest_complete') or dict()
        if isinstance(incomplete,dict) and incomplete.get('t') is not None:
            try:
                target_t=int(incomplete.get('t'))
            except Exception:
                target_t=None
            if target_t is not None:
                key=city+'|'+str(target_t)
                if key not in first_incomplete:
                    temps=list()
                    stations=incomplete.get('stations') or tuple()
                    for station in stations:
                        if not isinstance(station,dict):
                            continue
                        try:
                            temps.append(float(station.get('temp_f')))
                        except Exception:
                            continue
                    baseline=None
                    baseline_t=None
                    if isinstance(previous,dict):
                        try:
                            candidate_t=int(previous.get('t'))
                            candidate_v=float(previous.get('v'))
                            if candidate_t<target_t:
                                baseline=candidate_v
                                baseline_t=candidate_t
                        except Exception:
                            pass
                    station_mean=None
                    if temps:
                        station_mean=sum(temps)/len(temps)
                    first_incomplete[key]=dict(city=city,t=target_t,first_incomplete_at=retrieved,station_count=len(temps),station_mean=station_mean,baseline_v=baseline,baseline_t=baseline_t)
        complete=cityrow.get('latest_complete') or dict()
        if isinstance(complete,dict) and complete.get('t') is not None and complete.get('v') is not None:
            try:
                complete_t=int(complete.get('t'))
                complete_v=float(complete.get('v'))
            except Exception:
                complete_t=None
                complete_v=None
            if complete_t is not None and complete_v is not None:
                key=city+'|'+str(complete_t)
                targets[key]=dict(city=city,t=complete_t,target_v=complete_v,last_complete_at=retrieved)
                vals=complete_values.get(key)
                if not isinstance(vals,list):
                    vals=list()
                if not vals or vals[-1]!=complete_v:
                    vals.append(complete_v)
                complete_values[key]=vals

rows=list()
for key in sorted(first_incomplete):
    source=first_incomplete.get(key) or dict()
    target=targets.get(key)
    if not isinstance(target,dict):
        continue
    if source.get('station_mean') is None or source.get('baseline_v') is None:
        continue
    primary=float(source.get('station_mean'))
    baseline=float(source.get('baseline_v'))
    actual=float(target.get('target_v'))
    primary_error=primary-actual
    baseline_error=baseline-actual
    vals=complete_values.get(key) or list()
    rows.append(dict(city=source.get('city'),t=source.get('t'),first_incomplete_at=source.get('first_incomplete_at'),station_count=source.get('station_count'),station_mean=primary,baseline_v=baseline,baseline_t=source.get('baseline_t'),target_v=actual,primary_error=primary_error,baseline_error=baseline_error,primary_abs_error=abs(primary_error),baseline_abs_error=abs(baseline_error),target_revision_count=max(0,len(vals)-1)))

def metrics(subset):
    n=len(subset)
    if n==0:
        return dict(n=0)
    p_abs=[float(row.get('primary_abs_error')) for row in subset]
    b_abs=[float(row.get('baseline_abs_error')) for row in subset]
    p_err=[float(row.get('primary_error')) for row in subset]
    b_err=[float(row.get('baseline_error')) for row in subset]
    p_sq=[pow(value,2) for value in p_err]
    b_sq=[pow(value,2) for value in b_err]
    p_sorted=sorted(p_abs)
    b_sorted=sorted(b_abs)
    mid=n//2
    if n%2==1:
        p_med=p_sorted[mid]
        b_med=b_sorted[mid]
    else:
        p_med=(p_sorted[mid-1]+p_sorted[mid])/2
        b_med=(b_sorted[mid-1]+b_sorted[mid])/2
    return dict(n=n,primary_mae=sum(p_abs)/n,baseline_mae=sum(b_abs)/n,primary_rmse=math.sqrt(sum(p_sq)/n),baseline_rmse=math.sqrt(sum(b_sq)/n),primary_mean_signed_error=sum(p_err)/n,baseline_mean_signed_error=sum(b_err)/n,primary_median_absolute_error=p_med,baseline_median_absolute_error=b_med)

overall=metrics(rows)
by_city=dict()
city_wins=0
for city in ['chicago','miami','nyc']:
    subset=[row for row in rows if row.get('city')==city]
    item=metrics(subset)
    by_city[city]=item
    if item.get('n',0)>0 and float(item.get('primary_mae'))<float(item.get('baseline_mae')):
        city_wins+=1

by_station_count=dict()
counts=sorted(set(int(row.get('station_count')) for row in rows))
for count in counts:
    subset=[row for row in rows if int(row.get('station_count'))==count]
    by_station_count[str(count)]=metrics(subset)

overall_win=False
if overall.get('n',0)>0:
    overall_win=float(overall.get('primary_mae'))<float(overall.get('baseline_mae'))
survives=overall_win and city_wins>=2
revision_rows=len([row for row in rows if int(row.get('target_revision_count'))>0])

print('PROTOCOL_ID',protocol.get('protocol_id'))
print('MANIFEST_COUNT',len(files))
print('SCORABLE_PAIR_COUNT',len(rows))
print('TARGET_REVISION_PAIR_COUNT',revision_rows)
print('OVERALL_PRIMARY_MAE',overall.get('primary_mae'))
print('OVERALL_BASELINE_MAE',overall.get('baseline_mae'))
print('OVERALL_PRIMARY_RMSE',overall.get('primary_rmse'))
print('OVERALL_BASELINE_RMSE',overall.get('baseline_rmse'))
print('OVERALL_PRIMARY_MEAN_SIGNED_ERROR',overall.get('primary_mean_signed_error'))
print('OVERALL_BASELINE_MEAN_SIGNED_ERROR',overall.get('baseline_mean_signed_error'))
print('OVERALL_PRIMARY_MEDIAN_ABS_ERROR',overall.get('primary_median_absolute_error'))
print('OVERALL_BASELINE_MEDIAN_ABS_ERROR',overall.get('baseline_median_absolute_error'))
for city in ['chicago','miami','nyc']:
    item=by_city.get(city) or dict()
    print('CITY',city)
    print('CITY_N',item.get('n'))
    print('CITY_PRIMARY_MAE',item.get('primary_mae'))
    print('CITY_BASELINE_MAE',item.get('baseline_mae'))
    print('CITY_PRIMARY_RMSE',item.get('primary_rmse'))
    print('CITY_BASELINE_RMSE',item.get('baseline_rmse'))
    print('CITY_PRIMARY_WINS',item.get('n',0)>0 and float(item.get('primary_mae'))<float(item.get('baseline_mae')))
    print('---')
for count in sorted(by_station_count,key=lambda value:int(value)):
    item=by_station_count.get(count) or dict()
    print('STATION_COUNT',count,'N',item.get('n'),'PRIMARY_MAE',item.get('primary_mae'),'BASELINE_MAE',item.get('baseline_mae'))
print('CITY_WIN_COUNT',city_wins)
print('OVERALL_WIN',overall_win)
print('SURVIVAL_RULE_PASS',survives)
print('INTERPRETATION','DEVELOPMENT_FALSIFICATION_ONLY_NOT_HOLDOUT_NOT_MARKET_EDGE')

outdir=state/'analysis'
outdir.mkdir(parents=True,exist_ok=True)
out=outdir/'kwi-signal-feasibility-e367.json'
payload=dict(generated_at=datetime.now(timezone.utc).isoformat(),protocol_id=protocol.get('protocol_id'),manifest_count=len(files),scorable_pair_count=len(rows),target_revision_pair_count=revision_rows,overall=overall,by_city=by_city,by_station_count=by_station_count,city_win_count=city_wins,overall_win=overall_win,survival_rule_pass=survives,interpretation='development falsification only; serially correlated minute rows; no market edge inferred',rows=rows)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')
print('PATH',out)
print('KWI_SIGNAL_FEASIBILITY_SCORE_PASS')
