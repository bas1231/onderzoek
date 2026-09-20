from pathlib import Path
import json

root = Path.cwd()
base = root / 'knowledge/raw/market_data/polymarket'
files = sorted(base.glob('*.json'), key=lambda p: p.stat().st_mtime)
if not files:
    raise SystemExit('no_polymarket_snapshots')

path = files[-1]
data = json.loads(path.read_text(encoding='utf-8'))
books = data.get('books_response', [])
meta = data.get('token_metadata', {})

print('SNAPSHOT', path.name)
print('BOOK_COUNT', len(books))
if books:
    print('BOOK_KEYS', ','.join(sorted(books[0].keys())))

rows = []
for book in books:
    asset = str(book.get('asset_id') or book.get('token_id') or '')
    bids = book.get('bids') or []
    asks = book.get('asks') or []
    best_bid = max((float(x.get('price')) for x in bids), default=None)
    best_ask = min((float(x.get('price')) for x in asks), default=None)
    spread = None if best_bid is None or best_ask is None else best_ask - best_bid
    bid_depth = sum(float(x.get('size', 0)) for x in bids)
    ask_depth = sum(float(x.get('size', 0)) for x in asks)
    rows.append((spread if spread is not None else 999, asset, best_bid, best_ask, bid_depth, ask_depth, len(bids), len(asks)))

mapped = sum(1 for row in rows if row[1] in meta)
print('MAPPED_BOOKS', mapped)
spreads = [row[0] for row in rows if row[0] != 999]
if spreads:
    print('MIN_SPREAD', min(spreads))
    print('MAX_SPREAD', max(spreads))
    print('MEAN_SPREAD', sum(spreads) / len(spreads))

for row in sorted(rows)[:10]:
    spread, asset, bid, ask, bd, ad, nb, na = row
    info = meta.get(asset, {})
    print('BOOK', asset[:20], 'BID', bid, 'ASK', ask, 'SPREAD', spread, 'BID_DEPTH', round(bd,2), 'ASK_DEPTH', round(ad,2), 'LEVELS', nb, na)
    print('QUESTION', str(info.get('question',''))[:180])

crossed = sum(1 for row in rows if row[2] is not None and row[3] is not None and row[2] >= row[3])
print('CROSSED_BOOKS', crossed)
print('POLYMARKET_L2_ANALYSIS_PASS')
