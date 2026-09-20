from pathlib import Path
import json

root=Path.cwd()
base=root/'knowledge/raw/market_data/polymarket_neg_risk_manifests'
if not base.exists():
    raise SystemExit('manifest_dir_missing')
files=[p for p in base.iterdir() if p.is_file() and p.suffix=='.json']
files.sort(key=lambda p:p.stat().st_mtime)
if len(files)<2:
    raise SystemExit('not_enough_manifests')

latest=dict()
for p in files:
    try:
        data=json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        continue
    for row in data.get('groups') or tuple():
        if not isinstance(row,dict):
            continue
        eid=str(row.get('event_id') or '')
        title=str(row.get('title') or '').strip()
        if not eid or not title:
            continue
        latest[eid]=dict(event_id=eid,title=title,market_count=row.get('market_count'),group=row.get('neg_risk_market_id'),manifest=p.name)

def canonical(title):
    text=' '.join(title.strip().lower().split())
    if text.endswith(')') and '(' in text:
        pos=text.rfind('(')
        if pos>0:
            text=text[:pos].strip()
    return text

families=dict()
for eid,row in latest.items():
    key=canonical(str(row.get('title') or ''))
    bucket=families.get(key)
    if not isinstance(bucket,list):
        bucket=list()
    bucket.append(row)
    families[key]=bucket

multi=list()
for key,bucket in families.items():
    ids=set(str(row.get('event_id')) for row in bucket)
    if len(ids)>1:
        multi.append((key,bucket))
multi.sort(key=lambda item:(-len(item[1]),item[0]))

print('MANIFEST_COUNT',len(files))
print('UNIQUE_EVENT_COUNT',len(latest))
print('CROSS_SERIES_FAMILY_COUNT',len(multi))
for key,bucket in multi:
    print('FAMILY',key)
    print('EVENT_COUNT',len(bucket))
    ordered=sorted(bucket,key=lambda row:int(row.get('event_id')) if str(row.get('event_id')).isdigit() else str(row.get('event_id')))
    for row in ordered:
        print('EVENT',row.get('event_id'),'MARKETS',row.get('market_count'),'TITLE',row.get('title'),'GROUP',row.get('group'),'MANIFEST',row.get('manifest'))
    print('---')
print('CROSS_SERIES_SUBJECT_DISCOVERY_PASS')
