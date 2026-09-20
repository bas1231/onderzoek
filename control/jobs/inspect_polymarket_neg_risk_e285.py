from pathlib import Path
import json

root = Path.cwd()
base = root / 'knowledge/raw/market_data/polymarket'
files = sorted(base.glob('*.json'), key=lambda p: p.stat().st_mtime)
if not files:
    raise SystemExit('no_snapshot')

data = json.loads(files[-1].read_text(encoding='utf-8'))
books = data.get('books_response', [])
book_assets = {str(b.get('asset_id')) for b in books}

print('SNAPSHOT', files[-1].name)
print('BOOK_COUNT', len(books))
print('NEG_RISK_BOOKS', sum(1 for b in books if b.get('neg_risk') is True))

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
        present = [str(x) for x in ids if str(x) in book_assets]
        if present:
            matched.append((market, present))
    if not matched:
        continue
    neg = any((m.get('negRisk') is True or m.get('neg_risk') is True) for m,_ in matched)
    book_neg = any(next((b.get('neg_risk') for b in books if str(b.get('asset_id')) in ids), False) for ,ids in matched)
    if not neg and not book_neg and len(matched) < 2:
        continue
    print('EVENT_ID', event.get('id'))
    print('EVENT_TITLE', str(event.get('title',''))[:220])
    print('EVENT_KEYS', ','.join(sorted(k for k in event.keys() if 'risk' in k.lower() or 'market' in k.lower() or 'series' in k.lower())))
    print('TOTAL_MARKETS', len(event.get('markets', [])))
    print('MATCHED_MARKETS', len(matched))
    print('EVENT_NEG_FIELDS', {k:v for k,v in event.items() if 'risk' in k.lower()})
    for market,ids in matched:
        print('MARKET_ID', market.get('id'))
        print('QUESTION', str(market.get('question',''))[:220])
        print('MARKET_NEG_FIELDS', {k:v for k,v in market.items() if 'risk' in k.lower()})
        print('OUTCOMES', market.get('outcomes'))
        print('TOKENS_IN_BOOKS', ','.join(ids))
    print('---')
    shown += 1
    if shown >= 20:
        break

print('GROUPS_SHOWN', shown)
print('POLYMARKET_NEG_RISK_INSPECTION_PASS')
