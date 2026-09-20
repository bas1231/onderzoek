from pathlib import Path
import json

home=Path.home()
state=home/'.local/state/prediction-research'
manifest_dir=state/'kalshi_weather_index_manifests'

print('STATE_EXISTS',state.exists())
print('MANIFEST_DIR_EXISTS',manifest_dir.exists())
if not manifest_dir.exists():
    raise SystemExit('manifest_dir_missing')

print('STATE_CHILDREN')
for p in sorted(state.iterdir(),key=lambda x:x.name):
    try:
        kind='DIR' if p.is_dir() else 'FILE'
        size=p.stat().st_size if p.is_file() else 0
    except Exception:
        kind='UNKNOWN'
        size=-1
    print('STATE_CHILD',kind,p.name,size)

files=list()
for p in manifest_dir.iterdir():
    if p.is_file():
        files.append(p)
files.sort(key=lambda p:p.stat().st_mtime)
print('MANIFEST_FILE_COUNT',len(files))
for p in files[-12:]:
    print('MANIFEST_FILE',p.name,'SIZE',p.stat().st_size,'MTIME',p.stat().st_mtime)

for p in files[-5:]:
    print('OPEN_MANIFEST',p.name)
    try:
        text=p.read_text(encoding='utf-8',errors='replace')
    except Exception as exc:
        print('READ_ERROR',str(exc)[:500])
        continue
    try:
        data=json.loads(text)
    except Exception:
        print('NON_JSON_SAMPLE',text[:4000])
        continue
    if isinstance(data,dict):
        print('TOP_KEYS',sorted(data.keys()))
        for key in sorted(data.keys()):
            value=data.get(key)
            low=key.lower()
            if 'path' in low or 'raw' in low or 'file' in low or 'archive' in low or 'sha' in low or 'city' in low or 'retriev' in low or 'captur' in low:
                if isinstance(value,(dict,list)):
                    print('FIELD',key,json.dumps(value,sort_keys=True)[:6000])
                else:
                    print('FIELD',key,str(value)[:3000])
    else:
        print('TOP_KIND','LIST' if isinstance(data,list) else 'OTHER')
        print('SAMPLE',json.dumps(data,sort_keys=True)[:6000])
    print('---')

print('KWI_LOCAL_STATE_INSPECTION_PASS')
