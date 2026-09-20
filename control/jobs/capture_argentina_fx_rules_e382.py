from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone
import json

root=Path.cwd()
agent='PredictionEdgeHunter/1.0'
ids=['178817','189770']
outdir=root/'knowledge/raw/market_rules/polymarket'
outdir.mkdir(parents=True,exist_ok=True)
rows=dict()

for eid in ids:
    url='https:'+chr(47)+chr(47)+'gamma-api.polymarket.com/events/'+eid
    req=Request(url,headers={'User-Agent':agent})
    with urlopen(req,timeout=30) as response:
        body=response.read()
    data=json.loads(body)
    rows[eid]=data
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out=outdir/(stamp+'-event-'+eid+'.json')
    out.write_bytes(body)
    print('EVENT_PATH',eid,out)
    print('EVENT_ID',eid)
    print('EVENT_KEYS',sorted(data.keys()))
    for key in ['title','description','resolutionSource','startDate','endDate','negRisk','negRiskAugmented','negRiskMarketID']:
        print('EVENT_FIELD',eid,key,repr(data.get(key)))
    markets=data.get('markets') or tuple()
    print('MARKET_COUNT',eid,len(markets))
    for market in markets:
        if not isinstance(market,dict):
            continue
        print('MARKET_ID',eid,market.get('id'))
        for key in ['question','description','resolutionSource','endDate','negRisk','negRiskOther','negRiskMarketID','groupItemTitle']:
            print('MARKET_FIELD',eid,market.get('id'),key,repr(market.get(key)))
    print('---')

left=rows.get('178817') or dict()
right=rows.get('189770') or dict()
for key in ['description','resolutionSource','endDate']:
    print('EVENT_EQUAL',key,left.get(key)==right.get(key))
print('NEG_RISK_GROUP_EQUAL',left.get('negRiskMarketID')==right.get('negRiskMarketID'))
print('ARGENTINA_FX_RULE_CAPTURE_PASS')
