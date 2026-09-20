from pathlib import Path
from datetime import datetime,timezone
import asyncio
import json
import time

try:
    import websockets
except Exception as exc:
    print('WEBSOCKETS_IMPORT_FAILED',type(exc).name,str(exc))
    raise SystemExit('websockets_unavailable')

root=Path.cwd()
source=root/'knowledge/raw/market_data/polymarket_neg_risk_partial/20260920T013900Z106981.json'
if not source.exists():
    raise SystemExit('source_snapshot_missing')
data=json.loads(source.read_text(encoding='utf-8'))
markets=data.get('markets') or tuple()
if len(markets)!=3:
    raise SystemExit('market_count_wrong')

tokens=list()
for market in markets:
    token=str(market.get('yes_token') or '')
    if not token:
        raise SystemExit('yes_token_missing')
    tokens.append(token)

stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
outdir=root/'knowledge/raw/market_data/polymarket_shadow_smoke'
outdir.mkdir(parents=True,exist_ok=True)
out=outdir/(stamp+'106981.jsonl')

async def main():
    url='wss:'+chr(47)+chr(47)+'ws-subscriptions-clob.polymarket.com/ws/market'
    counts=dict()
    raw_frames=0
    pong_count=0
    start=time.monotonic()
    last_ping=start
    async with websockets.connect(url,ping_interval=None,close_timeout=5) as ws:
        sub=dict(assets_ids=tokens,type='market',custom_feature_enabled=True)
        await ws.send(json.dumps(sub))
        with out.open('a',encoding='utf-8') as fh:
            while time.monotonic()-start<60:
                now=time.monotonic()
                if now-last_ping>=10:
                    await ws.send('PING')
                    last_ping=now
                try:
                    msg=await asyncio.wait_for(ws.recv(),timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                received=datetime.now(timezone.utc).isoformat()
                if msg=='PONG':
                    pong_count+=1
                    fh.write(json.dumps(dict(received_at=received,raw='PONG'))+chr(10))
                    fh.flush()
                    continue
                raw_frames+=1
                fh.write(json.dumps(dict(received_at=received,raw=msg))+chr(10))
                fh.flush()
                try:
                    parsed=json.loads(msg)
                except Exception:
                    key='NON_JSON'
                    counts[key]=counts.get(key,0)+1
                    continue
                items=parsed if isinstance(parsed,list) else [parsed]
                for item in items:
                    if not isinstance(item,dict):
                        key='NON_OBJECT'
                    else:
                        key=str(item.get('event_type') or item.get('type') or 'UNKNOWN')
                    counts[key]=counts.get(key,0)+1
    print('RAW_FRAMES',raw_frames)
    print('PONG_COUNT',pong_count)
    for key in sorted(counts):
        print('EVENT_COUNT',key,counts.get(key))
    print('PATH',out)
    print('PROSPECTIVE_CUTOFF_CHECK',datetime.now(timezone.utc).isoformat())
    print('ASSET_MARKET_STREAM_SMOKE_PASS')

asyncio.run(main())
