from pathlib import Path
import os
import json

root=Path.cwd()
raw=root/'knowledge/raw'
if not raw.exists():
    raise SystemExit('raw_root_missing')

relevant=list()
for base,dirs,files in os.walk(raw):
    for name in files:
        low=name.lower()
        full=Path(base)/name
        rel=str(full.relative_to(root))
        rel_low=rel.lower()
        if 'kwi' in rel_low or 'weather_index' in rel_low or 'live_data' in rel_low:
            relevant.append(full)

relevant.sort(key=lambda p:str(p))
print('RELEVANT_FILE_COUNT',len(relevant))
for p in relevant[:200]:
    print('FILE',str(p.relative_to(root)))

json_files=[p for p in relevant if p.suffix.lower()=='.json']
print('JSON_FILE_COUNT',len(json_files))

city_counts=dict()
status_counts=dict()
pairish=list()
key_counts=dict()
parsed=0
for p in json_files:
    try:
        data=json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        continue
    parsed+=1
    if isinstance(data,dict):
        for key in data.keys():
            skey=str(key)
            key_counts[skey]=key_counts.get(skey,0)+1
        city=str(data.get('city') or data.get('location') or data.get('market') or '')
        if city:
            city_counts[city]=city_counts.get(city,0)+1
        status=str(data.get('status') or data.get('state') or data.get('reading_status') or '')
        if status:
            status_counts[status]=status_counts.get(status,0)+1
        text=json.dumps(data,sort_keys=True).lower()
        if 'incomplete' in text or 'canonical' in text or 'complete' in text:
            pairish.append(p)

print('PARSED_JSON_COUNT',parsed)
for city in sorted(city_counts):
    print('CITY_COUNT',city,city_counts.get(city))
for status in sorted(status_counts):
    print('STATUS_COUNT',status,status_counts.get(status))

print('COMMON_KEYS')
ordered=sorted(key_counts.items(),key=lambda item:(-item[1],item[0]))
for key,count in ordered[:80]:
    print('KEY_COUNT',key,count)

print('PAIRISH_FILE_COUNT',len(pairish))
for p in pairish[:80]:
    print('PAIRISH_FILE',str(p.relative_to(root)))
    try:
        data=json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        continue
    if isinstance(data,dict):
        print('PAIRISH_TOP_KEYS',sorted(data.keys()))
        for key in ['city','status','state','timestamp','retrieved_at','observed_at','latest_incomplete','canonical','complete']:
            if key in data:
                value=data.get(key)
                if isinstance(value,(dict,list)):
                    print('PAIRISH_FIELD',key,json.dumps(value,sort_keys=True)[:3000])
                else:
                    print('PAIRISH_FIELD',key,str(value)[:1000])
    print('---')

print('KWI_PAIR_INVENTORY_PASS')
