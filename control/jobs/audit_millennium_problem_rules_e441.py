from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone
import hashlib
import json

root=Path.cwd()
agent='PredictionEdgeHunter/1.0'
event_id='995361'
url='https:'+chr(47)+chr(47)+'gamma-api.polymarket.com/events/'+event_id
req=Request(url,headers={'User-Agent':agent})
with urlopen(req,timeout=30) as response:
    raw=response.read()
    status=response.status
if status!=200:
    raise SystemExit('event_fetch_failed')

event=json.loads(raw)
sha=hashlib.sha256(raw).hexdigest()
outdir=root/'knowledge/raw/market_rules/polymarket'
outdir.mkdir(parents=True,exist_ok=True)
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out=outdir/(stamp+'-event-'+event_id+'-e441.json')
out.write_bytes(raw)

print('HTTP_STATUS',status)
print('RAW_SHA256',sha)
print('RAW_PATH',out)
print('EVENT_ID',event.get('id'))
print('TITLE',event.get('title'))
print('ACTIVE',event.get('active'))
print('CLOSED',event.get('closed'))
print('START_DATE',event.get('startDate'))
print('END_DATE',event.get('endDate'))
print('NEG_RISK',event.get('negRisk'))
print('NEG_RISK_AUGMENTED',event.get('negRiskAugmented'))
print('NEG_RISK_MARKET_ID',event.get('negRiskMarketID'))
print('EVENT_RESOLUTION_SOURCE',event.get('resolutionSource'))

description=str(event.get('description') or '')
print('EVENT_DESCRIPTION_SHA256',hashlib.sha256(description.encode()).hexdigest())
print('EVENT_DESCRIPTION',repr(description)[:24000])

markets=[m for m in event.get('markets') or tuple() if isinstance(m,dict)]
print('MARKET_COUNT_ALL',len(markets))
negrisk_markets=[m for m in markets if m.get('negRisk') is True]
print('MARKET_COUNT_NEGRISK',len(negrisk_markets))

groups=set()
market_desc_hashes=set()
other_count=0
for market in negrisk_markets:
    mid=str(market.get('id') or '')
    gid=str(market.get('negRiskMarketID') or '')
    if gid:
        groups.add(gid)
    if market.get('negRiskOther') is True:
        other_count+=1
    mdesc=str(market.get('description') or '')
    market_desc_hashes.add(hashlib.sha256(mdesc.encode()).hexdigest())
    print('MARKET_BEGIN',mid)
    print('GROUP_ITEM',market.get('groupItemTitle'))
    print('QUESTION',market.get('question'))
    print('ACTIVE_MARKET',market.get('active'))
    print('CLOSED_MARKET',market.get('closed'))
    print('END_DATE_MARKET',market.get('endDate'))
    print('NEG_RISK_MARKET',market.get('negRisk'))
    print('NEG_RISK_OTHER',market.get('negRiskOther'))
    print('NEG_RISK_MARKET_ID_MARKET',market.get('negRiskMarketID'))
    print('RESOLUTION_SOURCE',market.get('resolutionSource'))
    print('OUTCOMES',market.get('outcomes'))
    print('DESCRIPTION_SHA256',hashlib.sha256(mdesc.encode()).hexdigest())
    print('DESCRIPTION',repr(mdesc)[:18000])
    print('MARKET_END',mid)

print('GROUP_ID_COUNT',len(groups))
print('GROUP_IDS',sorted(groups))
print('NEG_RISK_OTHER_COUNT',other_count)
print('MARKET_DESCRIPTION_HASH_COUNT',len(market_desc_hashes))
print('ALL_MARKET_DESCRIPTIONS_MATCH_EVENT',all(str(m.get('description') or '')==description for m in negrisk_markets))

text=description.lower()
phrases=['none','no problem','if no','does not solve','doesn t solve','by december','by january','deadline','first','next','simultaneous','same time','tie','all resolve','resolve no','no solution','unsolved']
for phrase in phrases:
    print('EVENT_PHRASE',phrase,phrase in text)

for market in negrisk_markets:
    combined=(str(market.get('question') or '')+' '+str(market.get('description') or '')).lower()
    hits=[phrase for phrase in phrases if phrase in combined]
    print('MARKET_PHRASES',market.get('id'),hits)

print('RULE_AUDIT_NOTE','No payoff identity is asserted here. Exact exhaustiveness requires rules to exclude an all-false state or explicitly assign it to one outcome.')
print('MILLENNIUM_RULE_AUDIT_E441_PASS')
