from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone
import json

root=Path.cwd()
cutoff=datetime.fromisoformat('2026-09-20T02:10:18.043370+00:00')
cutoff_epoch=cutoff.timestamp()
url='https:'+chr(47)+chr(47)+'data-api.polymarket.com/v2/trades?event_id=106981&limit=100'
req=Request(url,headers={'User-Agent':'PredictionEdgeHunter/1.0','Accept':'application/json'})
with urlopen(req,timeout=30) as r:
    raw=r.read()
    status=r.status

data=json.loads(raw)
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
outdir=root/'knowledge/raw/market_data/polymarket_trade_feed'
outdir.mkdir(parents=True,exist_ok=True)
out=outdir/(stamp+'106981.json')
out.write_bytes(raw)

print('HTTP',status)
print('TOP_TYPE',type(data).name)
if isinstance(data,dict):
    print('TOP_KEYS',sorted(data.keys()))
    rows=data.get('data') or tuple()
    pagination=data.get('pagination') or dict()
    print('PAGINATION',json.dumps(pagination,sort_keys=True)[:2000])
elif isinstance(data,list):
    rows=data
else:
    rows=tuple()
print('ROW_COUNT',len(rows))
post=0
for index,row in enumerate(rows[:20]):
    if not isinstance(row,dict):
        print('ROW',index,'NON_OBJECT',str(row)[:1000])
        continue
    print('ROW',index,'KEYS',sorted(row.keys()))
    print('ROW_SAMPLE',index,json.dumps(row,sort_keys=True)[:4000])
    ts=row.get('timestamp')
    if ts is None:
        ts=row.get('time')
    if ts is None:
        ts=row.get('created_at')
    try:
        value=float(ts)
        if value>1000000000000:
            value=value/1000.0
        if value>=cutoff_epoch:
            post+=1
    except Exception:
        pass
print('POST_PREREG_ROWS_FIRST20',post)
print('PREREG_EPOCH',cutoff_epoch)
print('PATH',out)
print('ASSET_TRADE_FEED_INSPECTION_PASS')
