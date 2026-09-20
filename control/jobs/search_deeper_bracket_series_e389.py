from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone
import json

root=Path.cwd()
agent='PredictionEdgeHunter/1.0'
base='https:'+chr(47)+chr(47)+'gamma-api.polymarket.com/events?active=true&closed=false&limit=100&offset='
matches=list()
seen=set()
scanned=0
pages=0

for off in [1500,1600,1700,1800,1900,2000,2100,2200,2300,2400,2500,2600,2700,2800,2900]:
    req=Request(base+str(off),headers={'User-Agent':agent})
    with urlopen(req,timeout=30) as response:
        page=json.loads(response.read())
    if not isinstance(page,list):
        raise SystemExit('unexpected_event_shape')
    pages+=1
    scanned+=len(page)
    if not page:
        print('EMPTY_PAGE_OFFSET',off)
        break
    for event in page:
        eid=str(event.get('id') or '')
        if not eid or eid in seen:
            continue
        seen.add(eid)
        title=str(event.get('title') or '')
        low=title.lower()
        interesting=('anthropic' in low) or ('higher brackets' in low) or ('lower brackets' in low)
        if not interesting:
            continue
        markets=event.get('markets') or tuple()
        neg_markets=list()
        groups=set()
        for market in markets:
            if not isinstance(market,dict):
                continue
            if market.get('negRisk') is not True:
                continue
            gid=str(market.get('negRiskMarketID') or '')
            if gid:
                groups.add(gid)
            neg_markets.append(dict(id=str(market.get('id') or ''),question=str(market.get('question') or ''),groupItemTitle=str(market.get('groupItemTitle') or ''),negRiskOther=market.get('negRiskOther')))
        matches.append(dict(event_id=eid,title=title,endDate=event.get('endDate'),negRisk=event.get('negRisk'),negRiskAugmented=event.get('negRiskAugmented'),negRiskMarketID=event.get('negRiskMarketID'),market_count=len(markets),neg_market_count=len(neg_markets),group_count=len(groups),markets=neg_markets,offset=off))

stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
outdir=root/'knowledge/raw/market_data/polymarket_cross_series_discovery'
outdir.mkdir(parents=True,exist_ok=True)
out=outdir/(stamp+'-deep-bracket-search.json')
payload=dict(retrieved_at=datetime.now(timezone.utc).isoformat(),offset_start=1500,offset_end=2900,pages_requested=15,pages_scanned=pages,raw_rows_scanned=scanned,unique_events_seen=len(seen),match_count=len(matches),live_trading=False,paid_actions=False,wallet_actions=False,matches=matches)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')

print('PAGES_SCANNED',pages)
print('RAW_ROWS_SCANNED',scanned)
print('UNIQUE_EVENTS_SEEN',len(seen))
print('MATCH_COUNT',len(matches))
for row in matches:
    print('EVENT',row.get('event_id'))
    print('TITLE',row.get('title'))
    print('OFFSET',row.get('offset'))
    print('END_DATE',row.get('endDate'))
    print('NEG_RISK',row.get('negRisk'))
    print('NEG_RISK_AUGMENTED',row.get('negRiskAugmented'))
    print('NEG_RISK_MARKET_ID',row.get('negRiskMarketID'))
    print('MARKET_COUNT',row.get('market_count'))
    print('NEG_MARKET_COUNT',row.get('neg_market_count'))
    for market in row.get('markets') or tuple():
        print('MARKET',market.get('id'),market.get('groupItemTitle'),market.get('question'))
    print('---')
print('PATH',out)
print('DEEP_BRACKET_SERIES_SEARCH_PASS')
