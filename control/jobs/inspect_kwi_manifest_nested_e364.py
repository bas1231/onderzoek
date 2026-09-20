from pathlib import Path
import json
import os

home=Path.home()
state=home/'.local/state/prediction-research'
manifests=state/'kalshi_weather_index_manifests'
raw=state/'raw'

files=list()
if manifests.exists():
    for p in manifests.iterdir():
        if p.is_file() and p.suffix=='.json':
            files.append(p)
files.sort(key=lambda p:p.stat().st_mtime)
if not files:
    raise SystemExit('no_kwi_manifests')
p=files[-1]
data=json.loads(p.read_text(encoding='utf-8'))

print('MANIFEST',p.name)
print('RETRIEVED_AT',data.get('retrieved_at'))
cities=data.get('cities') or tuple()
print('CITIES_KIND','LIST' if isinstance(cities,list) else 'DICT' if isinstance(cities,dict) else 'OTHER')

items=list()
if isinstance(cities,list):
    for row in cities:
        if isinstance(row,dict):
            items.append(row)
elif isinstance(cities,dict):
    for key,value in cities.items():
        if isinstance(value,dict):
            row=dict(value)
            row['city_key']=key
            items.append(row)

print('CITY_ENTRY_COUNT',len(items))
for index,row in enumerate(items):
    print('CITY_ENTRY',index)
    print('KEYS',sorted(row.keys()))
    for key in sorted(row.keys()):
        value=row.get(key)
        low=key.lower()
        if isinstance(value,(dict,list)):
            print('FIELD',key,json.dumps(value,sort_keys=True)[:9000])
        else:
            print('FIELD',key,str(value)[:3000])
    print('---')

print('RAW_EXISTS',raw.exists())
if raw.exists():
    dir_count=0
    file_count=0
    printed=0
    for base,dirs,names in os.walk(raw):
        rel=Path(base).relative_to(raw)
        dir_count+=1
        if printed<120:
            print('RAW_DIR',str(rel))
            printed+=1
        for name in sorted(names):
            file_count+=1
            if printed<220:
                fp=Path(base)/name
                try:
                    size=fp.stat().st_size
                except Exception:
                    size=-1
                print('RAW_FILE',str(fp.relative_to(raw)),'SIZE',size)
                printed+=1
    print('RAW_DIR_COUNT',dir_count)
    print('RAW_FILE_COUNT',file_count)
print('KWI_NESTED_MANIFEST_INSPECTION_PASS')
