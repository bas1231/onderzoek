from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone
import hashlib
import json

root=Path.cwd()
rule_dir=root/'knowledge/raw/market_rules/polymarket'
rule_dir.mkdir(parents=True,exist_ok=True)
agent='PredictionEdgeHunter/1.0'
event_ids=['48292','200252','507875']
events=dict()

for eid in event_ids:
    url='https:'+chr(47)+chr(47)+'gamma-api.polymarket.com/events/'+eid
    req=Request(url,headers={'User-Agent':agent})
    with urlopen(req,timeout=30) as response:
        body=response.read()
        status=response.status
    if status!=200:
        raise SystemExit('event_fetch_failed_'+eid)
    event=json.loads(body)
    events[eid]=event
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out=rule_dir/(stamp+'-event-'+eid+'.json')
    out.write_bytes(body)
    print('FETCHED',eid,'PATH',out)

for eid in event_ids:
    event=events[eid]
    desc=str(event.get('description') or '')
    print('EVENT_BEGIN',eid)
    print('TITLE',event.get('title'))
    print('END_DATE',event.get('endDate'))
    print('START_DATE',event.get('startDate'))
    print('NEG_RISK',event.get('negRisk'))
    print('NEG_RISK_AUGMENTED',event.get('negRiskAugmented'))
    print('NEG_RISK_MARKET_ID',event.get('negRiskMarketID'))
    print('DESCRIPTION_SHA256',hashlib.sha256(desc.encode()).hexdigest())
    print('DESCRIPTION_TEXT',repr(desc)[:12000])
    markets=event.get('markets') or tuple()
    print('MARKET_COUNT',len(markets))
    for market in markets:
        if not isinstance(market,dict):
            continue
        mdesc=str(market.get('description') or '')
        print('MARKET',market.get('id'))
        print('GROUP_ITEM',market.get('groupItemTitle'))
        print('QUESTION',market.get('question'))
        print('END_DATE_MARKET',market.get('endDate'))
        print('NEG_RISK_MARKET',market.get('negRisk'))
        print('NEG_RISK_OTHER',market.get('negRiskOther'))
        print('MARKET_DESCRIPTION_SHA256',hashlib.sha256(mdesc.encode()).hexdigest())
    print('EVENT_END',eid)

for left,right in [('48292','200252'),('48292','507875'),('200252','507875')]:
    a=events[left]
    b=events[right]
    ad=str(a.get('description') or '')
    bd=str(b.get('description') or '')
    print('PAIR',left,right)
    print('DESCRIPTION_EQUAL',ad==bd)
    print('END_DATE_EQUAL',str(a.get('endDate') or '')==str(b.get('endDate') or ''))
    print('NEG_RISK_BOTH',a.get('negRisk') is True and b.get('negRisk') is True)
    print('NON_AUGMENTED_BOTH',a.get('negRiskAugmented') is False and b.get('negRiskAugmented') is False)

for eid in event_ids:
    event=events[eid]
    hashes=set()
    for market in event.get('markets') or tuple():
        if isinstance(market,dict):
            text=str(market.get('description') or '')
            hashes.add(hashlib.sha256(text.encode()).hexdigest())
    print('EVENT_MARKET_DESCRIPTION_HASHES',eid,sorted(hashes))

print('OPENAI_IPO_SERIES_COMPARE_E411_PASS')
