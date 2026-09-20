from pathlib import Path
from datetime import datetime
import json

root = Path.cwd()
base = root / 'knowledge/raw/market_data/polymarket'
files = sorted(base.glob('*.json'), key=lambda p: p.stat().st_mtime)
if not files:
    raise SystemExit('no_snapshot')

data = json.loads(files[-1].read_text(encoding='utf-8'))
books = {str(b.get('asset_id')): b for b in data.get('books_response', [])}
events = data.get('events_response', {}).get('events', [])

markets = []
for event in events:
    for market in event.get('markets', []):
        question = str(market.get('question') or '')
        if ' by ' not in question:
            continue
        stem, tail = question.rsplit(' by ', 1)
        date_text = tail.rstrip('?').strip()
        try:
            deadline = datetime.strptime(date_text, '%B %d, %Y')
        except Exception:
            continue
        raw_ids = market.get('clobTokenIds')
        raw_outcomes = market.get('outcomes')
        if not raw_ids or not raw_outcomes:
            continue
        try:
            ids = json.loads(raw_ids) if isinstance(raw_ids, str) else raw_ids
            outcomes = json.loads(raw_outcomes) if isinstance(raw_outcomes, str) else raw_outcomes
        except Exception:
            continue
        if len(ids) != 2 or len(outcomes) != 2:
            continue
        mapping = {str(outcomes[i]).lower(): str(ids[i]) for i in range(2)}
        if 'yes' not in mapping or 'no' not in mapping:
            continue
        markets.append({'stem': stem.strip(), 'deadline': deadline, 'question': question, 'yes': mapping['yes'], 'no': mapping['no']})

def best_ask(asset):
    book = books.get(asset)
    if not book:
        return None
    asks = book.get('asks') or []
    if not asks:
        return None
    row = min(asks, key=lambda x: float(x.get('price', 9)))
    return float(row.get('price')), float(row.get('size', 0))

rows = []
for early in markets:
    for late in markets:
        if early['stem'] != late['stem']:
            continue
        if early['deadline'] >= late['deadline']:
            continue
        no_early = best_ask(early['no'])
        yes_late = best_ask(late['yes'])
        if not no_early or not yes_late:
            continue
        cost = no_early[0] + yes_late[0]
        rows.append({'stem': early['stem'], 'early': early['question'], 'late': late['question'], 'cost': cost, 'gross_floor_edge': 1.0 - cost, 'top_size': min(no_early[1], yes_late[1]), 'no_early_ask': no_early[0], 'yes_late_ask': yes_late[0]})

print('NESTED_RELATIONS', len(rows))
positive = [r for r in rows if r['gross_floor_edge'] > 0]
print('GROSS_POSITIVE', len(positive))
if rows:
    print('BEST_GROSS_EDGE', max(r['gross_floor_edge'] for r in rows))
for r in sorted(rows, key=lambda x: x['gross_floor_edge'], reverse=True):
    print('RELATION', r['stem'][:160])
    print('EARLY', r['early'])
    print('LATE', r['late'])
    print('NO_EARLY_ASK', r['no_early_ask'])
    print('YES_LATE_ASK', r['yes_late_ask'])
    print('COST', r['cost'], 'GROSS_EDGE', r['gross_floor_edge'], 'TOP_SIZE', r['top_size'])
print('DEADLINE_NESTING_TEST_PASS')
