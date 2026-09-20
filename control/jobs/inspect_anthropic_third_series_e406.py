from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone
import hashlib
import json

root=Path.cwd()
agent='PredictionEdgeHunter/1.0'
base=root/'knowledge/raw/market_rules/polymarket'
left_files=sorted(base.glob('*event-197776.json'),key=lambda p:p.stat().st_mtime)
mid_files=sorted(base.glob('*event-428957.json'),key=lambda p:p.stat().st_mtime)
if not left_files or not mid_files:
    raise SystemExit('prior_anthropic_rules_missing')
left=json.loads(left_files[-1].read_text(encoding='utf-8'))
mid=json.loads(mid_files[-1].read_text(encoding='utf-8'))

url='https:'+chr(47)+chr(47)+'gamma-api.polymarket.com/events/548858'
req=Request(url,headers={'User-Agent':agent})
with urlopen(req,timeout=30) as response:
    body=response.read()
    status=response.status
third=json.loads(body)
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out=base/(stamp+'-event-548858.json')
out.write_bytes(body)

for label,event in [('LOWER',left),('MIDDLE',mid),('THIRD',third)]:
    description=str(event.get('description') or '')
    print('SERIES',label)
    print('EVENT_ID',event.get('id'))
    print('TITLE',event.get('title'))
    print('END_DATE',event.get('endDate'))
    print('NEG_RISK',event.get('negRisk'))
    print('NEG_RISK_AUGMENTED',event.get('negRiskAugmented'))
    print('NEG_RISK_MARKET_ID',event.get('negRiskMarketID'))
    print('DESCRIPTION_SHA256',hashlib.sha256(description.encode()).hexdigest())
    print('MARKET_COUNT',len(event.get('markets') or tuple()))
    for market in event.get('markets') or tuple():
        if not isinstance(market,dict):
            continue
        print('MARKET',market.get('id'))
        print('GROUP_ITEM',market.get('groupItemTitle'))
        print('QUESTION',market.get('question'))
        print('END_DATE_MARKET',market.get('endDate'))
        print('NEG_RISK_MARKET',market.get('negRisk'))
        print('NEG_RISK_OTHER',market.get('negRiskOther'))
    print('---')

ld=str(left.get('description') or '')
md=str(mid.get('description') or '')
td=str(third.get('description') or '')
print('HTTP_STATUS',status)
print('THIRD_PATH',out)
print('LOWER_MIDDLE_DESCRIPTION_EQUAL',ld==md)
print('LOWER_THIRD_DESCRIPTION_EQUAL',ld==td)
print('MIDDLE_THIRD_DESCRIPTION_EQUAL',md==td)
print('ALL_END_DATE_EQUAL',left.get('endDate')==mid.get('endDate')==third.get('endDate'))
print('ALL_NEG_RISK',left.get('negRisk') is True and mid.get('negRisk') is True and third.get('negRisk') is True)
print('ALL_NON_AUGMENTED',left.get('negRiskAugmented') is False and mid.get('negRiskAugmented') is False and third.get('negRiskAugmented') is False)
print('GROUP_IDS_DISTINCT',len(set([str(left.get('negRiskMarketID')),str(mid.get('negRiskMarketID')),str(third.get('negRiskMarketID'))]))==3)
print('ANTHROPIC_THIRD_SERIES_INSPECT_PASS')
