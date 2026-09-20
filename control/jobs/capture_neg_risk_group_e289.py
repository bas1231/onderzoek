from pathlib import Path
from urllib.request import Request, urlopen
from datetime import datetime, timezone
import hashlib
import json

root = Path.cwd()
agent = 'PredictionEdgeHunter/1.0'
events_url = 'https://gamma-api.polymarket.com/events/keyset?closed=false&limit=100'
req = Request(events_url, headers={'User-Agent': agent})
with urlopen(req, timeout=30) as r:
    events_raw = r.read()
    events_status = r.status

data = json.loads(events_raw)
target = None
for event in data.get('events', []):
    if str(event.get('id')) == '48292':
        target = event
        break
if target is None:
    raise SystemExit('target_event_not_found')

markets = []
tokens = []
for market in target.get('markets', []):
    if market.get('negRisk') is not True:
        continue
    raw_ids = market.get('clobTokenIds')
    raw_outcomes = market.get('outcomes')
    ids = json.loads(raw_ids) if isinstance(raw_ids, str) else raw_ids
    outcomes = json.loads(raw_outcomes) if isinstance(raw_outcomes, str) else raw_outcomes
    if not ids or not outcomes or len(ids) != 2 or len(outcomes) != 2:
        continue
    markets.append({'id': market.get('id'), 'question': market.get('question'), 'outcomes': outcomes, 'tokens': ids, 'negRisk': market.get('negRisk'), 'negRiskOther': market.get('negRiskOther')})
    for token in ids:
        tokens.append({'token_id': str(token)})

if len(markets) != 7:
    raise SystemExit('unexpected_market_count')

books_url = 'https://clob.polymarket.com/books'
body = json.dumps(tokens).encode('utf-8')
req = Request(books_url, data=body, headers={'Content-Type': 'application/json', 'User-Agent': agent}, method='POST')
with urlopen(req, timeout=30) as r:
    books_raw = r.read()
    books_status = r.status
books = json.loads(books_raw)

stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
outdir = root / 'knowledge/raw/market_data/polymarket_neg_risk'
outdir.mkdir(parents=True, exist_ok=True)
out = outdir / (stamp + '48292.json')
payload = {'retrieved_at': datetime.now(timezone.utc).isoformat(), 'venue': 'polymarket', 'event_id': '48292', 'event_title': target.get('title'), 'mode': 'public_read_only', 'live_trading': False, 'paid_actions': False, 'wallet_actions': False, 'events_http_status': events_status, 'events_sha256': hashlib.sha256(events_raw).hexdigest(), 'books_http_status': books_status, 'books_sha256': hashlib.sha256(books_raw).hexdigest(), 'markets': markets, 'books': books}
out.write_text(json.dumps(payload, indent=2, sort_keys=True) + chr(10), encoding='utf-8')

book_map = {str(b.get('asset_id')): b for b in books}
print('NEG_RISK_GROUP_CAPTURE_PASS')
print('EVENT', target.get('title'))
print('MARKET_COUNT', len(markets))
print('BOOK_COUNT', len(books))
for market in markets:
    print('MARKET', market['id'], market['question'])
    print('OTHER', market['negRiskOther'])
    for i in range(2):
        token = str(market['tokens'][i])
        outcome = str(market['outcomes'][i])
        book = book_map.get(token)
        if not book:
            print('OUTCOME', outcome, 'NO_BOOK')
            continue
        bids = book.get('bids') or []
        asks = book.get('asks') or []
        bid = max((float(x.get('price')) for x in bids), default=None)
        ask = min((float(x.get('price')) for x in asks), default=None)
        print('OUTCOME', outcome, 'BID', bid, 'ASK', ask)
print('PATH', out)
