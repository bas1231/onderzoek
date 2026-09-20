from pathlib import Path
from urllib.request import Request, urlopen
from datetime import datetime, timezone
import json

root = Path.cwd()
agent = 'PredictionEdgeHunter/1.0'
events = []
seen = set()

for offset in range(0,500,100):
    url = 'https://gamma-api.polymarket.com/events?active=true&closed=false&limit=100&offset=' + str(offset)
    req = Request(url, headers={'User-Agent':agent})
    with urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    page = data if isinstance(data,list) else data.get('events',[])
    if not page:
        break
    for event in page:
        eid = str(event.get('id'))
        if eid not in seen:
            seen.add(eid)
            events.append(event)
    if len(page) < 100:
        break

eligible = []
for event in events:
    if event.get('negRisk') is not True:
        continue
    if event.get('negRiskAugmented') is True:
        continue
    markets = event.get('markets') or []
    neg = []
    market_ids = set()
    valid = True
    for market in markets:
        if market.get('negRisk') is not True:
            continue
        rid = str(market.get('negRiskMarketID') or '')
        if rid:
            market_ids.add(rid)
        raw_ids = market.get('clobTokenIds')
        raw_outcomes = market.get('outcomes')
        try:
            ids = json.loads(raw_ids) if isinstance(raw_ids,str) else raw_ids
            outcomes = json.loads(raw_outcomes) if isinstance(raw_outcomes,str) else raw_outcomes
        except Exception:
            valid = False
            break
        if not ids or not outcomes or len(ids) != 2 or len(outcomes) != 2:
            valid = False
            break
        names = [str(x).lower() for x in outcomes]
        if 'yes' not in names or 'no' not in names:
            valid = False
            break
        mapping = {names[i]:str(ids[i]) for i in range(2)}
        neg.append({'id':str(market.get('id')),'question':str(market.get('question') or ''),'yes':mapping,'no':mapping})
    if not valid:
        continue
    if len(neg) < 3 or len(neg) > 40:
        continue
    if len(market_ids) != 1:
        continue
    eligible.append({'event_id':str(event.get('id')),'title':str(event.get('title') or ''),'markets':neg,'neg_risk_market_id':next(iter(market_ids))})

eligible.sort(key=lambda x:(len(x['markets']),x['event_id']))
selected = eligible[:30]
results = []

for event in selected:
    tokens = []
    for market in event['markets']:
        tokens.append({'token_id':market})
        tokens.append({'token_id':market})
    body = json.dumps(tokens).encode('utf-8')
    req = Request('https://clob.polymarket.com/books', data=body, headers={'Content-Type':'application/json','User-Agent':agent}, method='POST')
    try:
        with urlopen(req, timeout=30) as r:
            books = json.loads(r.read())
    except Exception as exc:
        results.append({'event_id':event,'title':event,'status':'BOOK_FETCH_FAILED','error':type(exc).name})
        continue
    bookmap = {str(b.get('asset_id')):b for b in books}
    rows = []
    complete = True
    for market in event['markets']:
        row = {'id':market,'question':market}
        for side in ['yes','no']:
            book = bookmap.get(market[side])
            if not book:
                complete = False
                break
            bids = book.get('bids') or []
            asks = book.get('asks') or []
            if not bids or not asks:
                complete = False
                break
            bid = max(bids,key=lambda x:float(x.get('price',0)))
            ask = min(asks,key=lambda x:float(x.get('price',9)))
            row[side] = {'bid':float(bid.get('price')),'bid_size':float(bid.get('size',0)),'ask':float(ask.get('price')),'ask_size':float(ask.get('size',0))}
        if not complete:
            break
        rows.append(row)
    if not complete or len(rows) != len(event['markets']):
        results.append({'event_id':event,'title':event,'status':'INCOMPLETE_BOOKS','market_count':len(event['markets'])})
        continue
    n = len(rows)
    yes_cost = sum(r['yes']['ask'] for r in rows)
    no_cost = sum(r['no']['ask'] for r in rows)
    yes_edge = 1.0 - yes_cost
    no_edge = float(n-1) - no_cost
    yes_size = min(r['yes']['ask_size'] for r in rows)
    no_size = min(r['no']['ask_size'] for r in rows)
    results.append({'event_id':event,'title':event,'status':'PRICED','market_count':n,'yes_ask_cost':yes_cost,'yes_gross_edge':yes_edge,'yes_top_size':yes_size,'no_ask_cost':no_cost,'no_gross_edge':no_edge,'no_top_size':no_size})

stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
outdir = root / 'knowledge/raw/market_data/polymarket_neg_risk_scans'
outdir.mkdir(parents=True, exist_ok=True)
out = outdir / (stamp + '.json')
payload = {'retrieved_at':datetime.now(timezone.utc).isoformat(),'events_scanned':len(events),'eligible_groups':len(eligible),'groups_priced_attempted':len(selected),'live_trading':False,'paid_actions':False,'wallet_actions':False,'results':results}
out.write_text(json.dumps(payload,indent=2,sort_keys=True) + chr(10),encoding='utf-8')

priced = [r for r in results if r.get('status') == 'PRICED']
positive = [r for r in priced if r.get('yes_gross_edge',0) > 0 or r.get('no_gross_edge',0) > 0]
print('NEG_RISK_BROAD_SCAN_PASS')
print('EVENTS_SCANNED',len(events))
print('ELIGIBLE_GROUPS',len(eligible))
print('GROUPS_ATTEMPTED',len(selected))
print('GROUPS_PRICED',len(priced))
print('GROSS_POSITIVE_GROUPS',len(positive))
if priced:
    best_yes = max(priced,key=lambda x:x)
    best_no = max(priced,key=lambda x:x)
    print('BEST_YES',best_yes['event_id'],best_yes['yes_gross_edge'],best_yes['yes_top_size'],best_yes['title'][:180])
    print('BEST_NO',best_no['event_id'],best_no['no_gross_edge'],best_no['no_top_size'],best_no['title'][:180])
for row in positive:
    print('CANDIDATE',row['event_id'],row['market_count'],row['yes_gross_edge'],row['no_gross_edge'],row['title'][:180])
print('PATH',out)
