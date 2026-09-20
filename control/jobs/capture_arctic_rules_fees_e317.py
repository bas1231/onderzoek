from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone
import json

root=Path.cwd()
url='https:'+chr(47)+chr(47)+'gamma-api.polymarket.com/events/86426'
req=Request(url,headers={'User-Agent':'PredictionEdgeHunter/1.0'})
with urlopen(req,timeout=30) as r:
    raw=r.read()
    status=r.status

event=json.loads(raw)
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
outdir=root/'knowledge/raw/market_rules/polymarket'
outdir.mkdir(parents=True,exist_ok=True)
out=outdir/(stamp+'event_86426.json')
out.write_bytes(raw)

print('ARCTIC_RULE_FEE_CAPTURE_PASS')
print('HTTP',status)
print('EVENT_ID',event.get('id'))
print('TITLE',event.get('title'))
print('NEG_RISK',event.get('negRisk'))
print('NEG_RISK_AUGMENTED',event.get('negRiskAugmented'))
print('NEG_RISK_MARKET_ID',event.get('negRiskMarketID'))
print('DESCRIPTION')
print(str(event.get('description') or '')[:12000])
markets=event.get('markets') or tuple()
print('MARKET_COUNT',len(markets))
for market in markets:
    print('MARKET_ID',market.get('id'))
    print('QUESTION',market.get('question'))
    print('NEG_RISK',market.get('negRisk'))
    print('NEG_RISK_OTHER',market.get('negRiskOther'))
    print('FEES_ENABLED',market.get('feesEnabled'))
    print('FEE_SCHEDULE',market.get('feeSchedule'))
    print('FEE_TYPE',market.get('feeType'))
    print('ORDER_MIN_SIZE',market.get('orderMinSize'))
    print('TICK_SIZE',market.get('orderPriceMinTickSize'))
    print('END_DATE',market.get('endDate'))
    desc=str(market.get('description') or '').replace(chr(10),' ')
    print('DESCRIPTION',desc[:6000])
    print('---')
print('PATH',out)
