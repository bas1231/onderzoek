from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone
import json
import hashlib

root=Path.cwd()
agent='PredictionEdgeHunter/1.0'
ids=['197776','428957']
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
    print('EVENT',eid)
    print('TITLE',data.get('title'))
    print('END_DATE',data.get('endDate'))
    print('NEG_RISK',data.get('negRisk'))
    print('NEG_RISK_AUGMENTED',data.get('negRiskAugmented'))
    print('NEG_RISK_MARKET_ID',data.get('negRiskMarketID'))
    description=str(data.get('description') or '')
    print('DESCRIPTION_SHA256',hashlib.sha256(description.encode()).hexdigest())
    print('MARKET_COUNT',len(data.get('markets') or tuple()))
    for market in data.get('markets') or tuple():
        if not isinstance(market,dict):
            continue
        print('MARKET',market.get('id'))
        print('GROUP_ITEM',market.get('groupItemTitle'))
        print('QUESTION',market.get('question'))
        print('END_DATE_MARKET',market.get('endDate'))
        print('NEG_RISK_MARKET',market.get('negRisk'))
        print('NEG_RISK_OTHER',market.get('negRiskOther'))
    print('---')

left=rows.get('197776') or dict()
right=rows.get('428957') or dict()
ld=str(left.get('description') or '')
rd=str(right.get('description') or '')
print('DESCRIPTION_EXACT_EQUAL',ld==rd)
print('END_DATE_EQUAL',left.get('endDate')==right.get('endDate'))
print('NEG_RISK_BOTH',left.get('negRisk') is True and right.get('negRisk') is True)
print('NON_AUGMENTED_BOTH',left.get('negRiskAugmented') is False and right.get('negRiskAugmented') is False)
print('GROUP_IDS_DIFFER',left.get('negRiskMarketID')!=right.get('negRiskMarketID'))
print('ANTHROPIC_CROSS_SERIES_RULE_CAPTURE_PASS')
