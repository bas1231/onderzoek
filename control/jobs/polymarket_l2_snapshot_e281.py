from pathlib import Path
from urllib.request import Request, urlopen
from datetime import datetime, timezone
import hashlib
import json

root = Path.cwd()
agent = 'PredictionEdgeHunter/1.0'
events_url = 'https://gamma-api.polymarket.com/events/keyset?closed=false&limit=20'
books_url = 'https://clob.polymarket.com/books'

req = Request(events_url, headers={'User-Agent': agent})
with urlopen(req, timeout=30) as r:
    events_raw = r.read()
    events_status = r.status

events = json.loads(events_raw)
tokens = []
meta = {}
for event in events.get('events', []):
    for market in event.get('markets', []):
        raw_ids = market.get('clobTokenIds')
        if not raw_ids:
            continue
        try:
            ids = json.loads(raw_ids) if isinstance(raw_ids, str) else raw_ids
        except Exception:
            continue
        for token in ids:
            token = str(token)
            if token in meta:
                continue
            meta[token] = {
                'event_id': event.get('id'),
                'event_title': event.get('title'),
                'market_id': market.get('id'),
                'question': market.get('question'),
                'condition_id': market.get('conditionId')
            }
            tokens.append({'token_id': token})
            if len(tokens) >= 50:
                break
        if len(tokens) >= 50:
            break
    if len(tokens) >= 50:
        break

if not tokens:
    raise SystemExit('no_token_ids_discovered')

body = json.dumps(tokens).encode('utf-8')
req = Request(books_url, data=body, headers={'Content-Type': 'application/json', 'User-Agent': agent}, method='POST')
with urlopen(req, timeout=30) as r:
    books_raw = r.read()
    books_status = r.status

books = json.loads(books_raw)
if not isinstance(books, list):
    raise SystemExit('unexpected_books_shape')

stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
outdir = root / 'knowledge/raw/market_data/polymarket'
outdir.mkdir(parents=True, exist_ok=True)
out = outdir / (stamp + '.json')
payload = {
    'retrieved_at': datetime.now(timezone.utc).isoformat(),
    'venue': 'polymarket',
    'mode': 'public_read_only',
    'live_trading': False,
    'paid_actions': False,
    'wallet_actions': False,
    'events_url': events_url,
    'events_http_status': events_status,
    'events_sha256': hashlib.sha256(events_raw).hexdigest(),
    'books_url': books_url,
    'books_http_status': books_status,
    'books_sha256': hashlib.sha256(books_raw).hexdigest(),
    'requested_token_count': len(tokens),
    'returned_book_count': len(books),
    'token_metadata': meta,
    'events_response': events,
    'books_response': books
}
out.write_text(json.dumps(payload, indent=2, sort_keys=True) + chr(10), encoding='utf-8')

with_bid = sum(1 for b in books if b.get('bids'))
with_ask = sum(1 for b in books if b.get('asks'))
with_both = sum(1 for b in books if b.get('bids') and b.get('asks'))
print('POLYMARKET_L2_SNAPSHOT_PASS')
print('PATH', out)
print('EVENTS_HTTP', events_status)
print('BOOKS_HTTP', books_status)
print('REQUESTED_TOKENS', len(tokens))
print('RETURNED_BOOKS', len(books))
print('BOOKS_WITH_BID', with_bid)
print('BOOKS_WITH_ASK', with_ask)
print('BOOKS_WITH_BOTH', with_both)
