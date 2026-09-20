from pathlib import Path
from datetime import datetime
import json

root=Path.cwd()
base=root/'knowledge/raw/market_data/polymarket_trade_feed'
files=list()
if base.exists():
    for p in base.iterdir():
        if p.is_file() and '106981' in p.name and p.suffix=='.json':
            files.append(p)
files.sort(key=lambda p:p.stat().st_mtime)
if not files:
    raise SystemExit('trade_archive_missing')
p=files[-1]
data=json.loads(p.read_text(encoding='utf-8'))
cutoff=datetime.fromisoformat('2026-09-20T02:10:18.043370+00:00').timestamp()

if isinstance(data,dict):
    print('TOP_KIND','DICT')
    print('TOP_KEYS',sorted(data.keys()))
    rows=data.get('data') or data.get('trades') or tuple()
elif isinstance(data,list):
    print('TOP_KIND','LIST')
    rows=data
else:
    print('TOP_KIND','OTHER')
    rows=tuple()

print('ARCHIVE',p.name)
print('ROW_COUNT',len(rows))
post=0
ids=set()
assets=set()
for index,row in enumerate(rows[:30]):
    if not isinstance(row,dict):
        print('ROW',index,'NON_OBJECT')
        continue
    print('ROW',index,'KEYS',sorted(row.keys()))
    print('ROW_SAMPLE',index,json.dumps(row,sort_keys=True)[:5000])
    for key in ['event_id','eventId','event','condition_id','conditionId','market','market_id','marketId']:
        value=row.get(key)
        if value is not None:
            ids.add(str(value))
    for key in ['asset_id','assetId','token_id','tokenId']:
        value=row.get(key)
        if value is not None:
            assets.add(str(value))
    ts=None
    for key in ['timestamp','time','created_at','createdAt']:
        if row.get(key) is not None:
            ts=row.get(key)
            break
    try:
        value=float(ts)
        if value>1000000000000:
            value=value/1000.0
        if value>=cutoff:
            post+=1
    except Exception:
        pass
print('ID_VALUES',sorted(ids)[:30])
print('ASSET_COUNT',len(assets))
print('POST_PREREG_FIRST30',post)
print('PREREG_EPOCH',cutoff)
print('ASSET_TRADE_ARCHIVE_INSPECTION_PASS')
