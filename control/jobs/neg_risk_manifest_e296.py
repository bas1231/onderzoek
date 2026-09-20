from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone
import json

root=Path.cwd()
agent='PredictionEdgeHunter/1.0'
base='https:'+chr(47)+chr(47)+'gamma-api.polymarket.com/events?active=true&closed=false&limit=100&offset='
seen=set()
eligible=[]
scanned=0

for off in [0,100,200,300,400]:
    req=Request(base+str(off),headers={'User-Agent':agent})
    with urlopen(req,timeout=30) as r:
        page=json.loads(r.read())
    if not isinstance(page,list):
        raise SystemExit('unexpected_event_shape')
    scanned+=len(page)
    for event in page:
        eid=str(event.get('id'))
        if eid in seen:
            continue
        seen.add(eid)
        if event.get('negRisk') is not True:
            continue
        if event.get('negRiskAugmented') is True:
            continue
        markets=[]
        groups=set()
        for market in event.get('markets') or []:
            if market.get('negRisk') is not True:
                continue
            ids=market.get('clobTokenIds')
            outs=market.get('outcomes')
            if isinstance(ids,str):
                ids=json.loads(ids)
            if isinstance(outs,str):
                outs=json.loads(outs)
            if not ids or not outs or len(ids)!=2 or len(outs)!=2:
                continue
            names=[str(x).lower() for x in outs]
            if 'yes' not in names or 'no' not in names:
                continue
            yi=names.index('yes')
            ni=names.index('no')
            gid=str(market.get('negRiskMarketID') or '')
            if gid:
                groups.add(gid)
            markets.append({'market_id':str(market.get('id')),'question':str(market.get('question') or ''),'yes_token':str(ids[yi]),'no_token':str(ids[ni])})
        if len(markets)>=3 and len(markets)<=40 and len(groups)==1:
            eligible.append({'event_id':eid,'title':str(event.get('title') or ''),'neg_risk_market_id':next(iter(groups)),'market_count':len(markets),'markets':markets})

stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
outdir=root/'knowledge/raw/market_data/polymarket_neg_risk_manifests'
outdir.mkdir(parents=True,exist_ok=True)
out=outdir/(stamp+'.json')
payload={'retrieved_at':datetime.now(timezone.utc).isoformat(),'events_seen':len(seen),'raw_rows_scanned':scanned,'eligible_group_count':len(eligible),'live_trading':False,'paid_actions':False,'wallet_actions':False,'groups':eligible}
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')

print('NEG_RISK_MANIFEST_PASS')
print('EVENTS_SEEN',len(seen))
print('RAW_ROWS_SCANNED',scanned)
print('ELIGIBLE_GROUPS',len(eligible))
for row in eligible[:15]:
    print('GROUP',row['event_id'],row['market_count'],row['title'][:160])
print('PATH',out)
