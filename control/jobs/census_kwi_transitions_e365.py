from pathlib import Path
from datetime import datetime,timezone
import json
import os

home=Path.home()
state=home/'.local/state/prediction-research'
manifests=state/'kalshi_weather_index_manifests'
raw=state/'raw'
if not manifests.exists():
    raise SystemExit('manifest_dir_missing')

files=[p for p in manifests.iterdir() if p.is_file() and p.suffix=='.json']
files.sort(key=lambda p:p.stat().st_mtime)
print('MANIFEST_COUNT',len(files))

states=dict()
sha_values=set()
revision_flags=0
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
        sha=str(cityrow.get('sha256') or '')
        if sha:
            sha_values.add(sha)
        if cityrow.get('latest_complete_v_changed_for_same_t') is True:
            revision_flags+=1
        incomplete=cityrow.get('latest_incomplete') or dict()
        complete=cityrow.get('latest_complete') or dict()
        if isinstance(incomplete,dict) and incomplete.get('t') is not None:
            try:
                t=int(incomplete.get('t'))
            except Exception:
                t=None
            if t is not None:
                key=(city,t)
                rec=states.get(key)
                if rec is None:
                    rec=dict(city=city,t=t,first_incomplete_at=None,first_incomplete_stations=list(),first_complete_at=None,first_complete_v=None,last_complete_at=None,last_complete_v=None,complete_values=list())
                    states[key]=rec
                if rec.get('first_incomplete_at') is None:
                    rec['first_incomplete_at']=retrieved
                    stations=incomplete.get('stations') or tuple()
                    vals=list()
                    for station in stations:
                        if not isinstance(station,dict):
                            continue
                        try:
                            temp=float(station.get('temp_f'))
                        except Exception:
                            continue
                        vals.append(dict(station_id=str(station.get('station_id') or ''),temp_f=temp,code=str(station.get('code') or ''),received_at_ms=station.get('received_at_ms')))
                    rec['first_incomplete_stations']=vals
        if isinstance(complete,dict) and complete.get('t') is not None and complete.get('v') is not None:
            try:
                t=int(complete.get('t'))
                value=float(complete.get('v'))
            except Exception:
                t=None
                value=None
            if t is not None and value is not None:
                key=(city,t)
                rec=states.get(key)
                if rec is None:
                    rec=dict(city=city,t=t,first_incomplete_at=None,first_incomplete_stations=list(),first_complete_at=None,first_complete_v=None,last_complete_at=None,last_complete_v=None,complete_values=list())
                    states[key]=rec
                if rec.get('first_complete_at') is None:
                    rec['first_complete_at']=retrieved
                    rec['first_complete_v']=value
                rec['last_complete_at']=retrieved
                rec['last_complete_v']=value
                vals=rec.get('complete_values') or list()
                if not vals or vals[-1]!=value:
                    vals.append(value)
                rec['complete_values']=vals

pairs=list()
for key in sorted(states):
    rec=states.get(key)
    if rec.get('first_incomplete_at') is None or rec.get('first_complete_at') is None:
        continue
    try:
        a=datetime.fromisoformat(rec.get('first_incomplete_at'))
        b=datetime.fromisoformat(rec.get('first_complete_at'))
        latency=(b-a).total_seconds()
    except Exception:
        latency=None
    rec['latency_seconds']=latency
    rec['station_count']=len(rec.get('first_incomplete_stations') or tuple())
    rec['revised_after_first_complete']=len(rec.get('complete_values') or tuple())>1
    pairs.append(rec)

print('STATE_COUNT',len(states))
print('MATCHED_PAIR_COUNT',len(pairs))
print('MANIFEST_REVISION_FLAG_COUNT',revision_flags)
for city in sorted(set(rec.get('city') for rec in pairs)):
    subset=[rec for rec in pairs if rec.get('city')==city]
    revised=[rec for rec in subset if rec.get('revised_after_first_complete')]
    lat=[rec.get('latency_seconds') for rec in subset if rec.get('latency_seconds') is not None]
    stations=[rec.get('station_count') for rec in subset]
    print('CITY',city)
    print('PAIR_COUNT',len(subset))
    print('REVISED_PAIR_COUNT',len(revised))
    if lat:
        print('LATENCY_MIN',min(lat))
        print('LATENCY_MAX',max(lat))
        print('LATENCY_MEAN',sum(lat)/len(lat))
    if stations:
        print('STATION_COUNT_MIN',min(stations))
        print('STATION_COUNT_MAX',max(stations))
    print('---')

for rec in pairs[:20]:
    print('PAIR',rec.get('city'),rec.get('t'),rec.get('first_incomplete_at'),rec.get('first_complete_at'),rec.get('latency_seconds'),rec.get('station_count'),rec.get('first_complete_v'),rec.get('last_complete_v'),rec.get('complete_values'))

raw_names=set()
if raw.exists():
    for base,dirs,names in os.walk(raw):
        for name in names:
            stem=Path(name).stem
            if len(stem)==64:
                raw_names.add(stem)
matched_sha=len([value for value in sha_values if value in raw_names])
print('UNIQUE_MANIFEST_SHA_COUNT',len(sha_values))
print('RAW_HASH_NAME_COUNT',len(raw_names))
print('MANIFEST_SHA_FOUND_AS_RAW_FILENAME',matched_sha)

outdir=state/'analysis'
outdir.mkdir(parents=True,exist_ok=True)
out=outdir/'kwi-transition-census-e365.json'
payload=dict(generated_at=datetime.now(timezone.utc).isoformat(),manifest_count=len(files),state_count=len(states),matched_pair_count=len(pairs),manifest_revision_flag_count=revision_flags,unique_manifest_sha_count=len(sha_values),manifest_sha_found_as_raw_filename=matched_sha,pairs=pairs)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')
print('PATH',out)
print('KWI_TRANSITION_CENSUS_PASS')
