from pathlib import Path
import json

root = Path.cwd()
base = root / 'knowledge/raw/market_data/polymarket'
files = sorted(base.glob('*.json'), key=lambda p: p.stat().st_mtime)
if not files:
    raise SystemExit('no_snapshot')

data = json.loads(files[-1].read_text(encoding='utf-8'))
books = data.get('books_response', [])
assets = set()
neg_assets = set()
for book in books:
    asset = str(book.get('asset_id'))
    assets.add(asset)
    if book.get('neg_risk') is True:
        neg_assets.add(asset)

print('SNAPSHOT', files[-1].name)
print('BOOK_COUNT', len(books))
print('NEG_RISK_BOOKS', len(neg_assets))

shown = 0
for event in data.get('events_response', {}).get('events', []):
    matched = []
    for market in event.get('markets', []):
        raw_ids = market.get('clobTokenIds')
        if not raw_ids:
            continue
        try:
            ids = json.loads(raw_ids) if isinstance(raw_ids, str) else raw_ids
        except Exception:
            continue
        present = []
        for token in ids:
            token = str(token)
            if token in assets:
                present.append(token)
        if present:
            matched.append({'market': market, 'tokens': present})
    if not matched:
        continue
    event_neg = False
    for key,value in event.items():
        if 'risk' in key.lower() and value is True:
            event_neg = True
    matched_neg = False
    for item in matched:
        for token in item['tokens']:
            if token in neg_assets:
                matched_neg = True
    if not event_neg and not matched_neg and len(matched) < 2:
        continue
    print('EVENT_ID', event.get('id'))
    print('EVENT_TITLE', str(event.get('title',''))[:220])
    print('TOTAL_MARKETS', len(event.get('markets', [])))
    print('MATCHED_MARKETS', len(matched))
    print('EVENT_NEG', event_neg)
    print('BOOK_NEG', matched_neg)
    for item in matched:
        market = item['market']
        print('MARKET_ID', market.get('id'))
        print('QUESTION', str(market.get('question',''))[:220])
        print('OUTCOMES', market.get('outcomes'))
        print('TOKENS', ','.join(item['tokens']))
        for key,value in market.items():
            if 'risk' in key.lower():
                print('RISK_FIELD', key, value)
    print('---')
    shown += 1
    if shown >= 20:
        break

print('GROUPS_SHOWN', shown)
print('NEG_RISK_INSPECTION_PASS')
