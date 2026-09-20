from pathlib import Path
import json

root = Path.cwd()
base = root / 'knowledge/raw/market_data/polymarket'
files = sorted(base.glob('*.json'), key=lambda p: p.stat().st_mtime)
if not files:
    raise SystemExit('no_snapshot')

data = json.loads(files[-1].read_text(encoding='utf-8'))
books = {str(b.get('asset_id')): b for b in data.get('books_response', [])}
events = data.get('events_response', {}).get('events', [])

rows = []
for event in events:
    for market in event.get('markets', []):
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
        a = books.get(str(ids[0]))
        b = books.get(str(ids[1]))
        if not a or not b:
            continue
        def top(book):
            bids = book.get('bids') or []
            asks = book.get('asks') or []
            if not bids or not asks:
                return None
            bid = max(bids, key=lambda x: float(x.get('price', 0)))
            ask = min(asks, key=lambda x: float(x.get('price', 9)))
            return float(bid['price']), float(bid['size']), float(ask['price']), float(ask['size'])
        ta = top(a)
        tb = top(b)
        if not ta or not tb:
            continue
        bid_a, bid_size_a, ask_a, ask_size_a = ta
        bid_b, bid_size_b, ask_b, ask_size_b = tb
        buy_sum = ask_a + ask_b
        sell_sum = bid_a + bid_b
        rows.append({
            'question': market.get('question'),
            'outcomes': outcomes,
            'buy_both_cost': buy_sum,
            'buy_both_gross_edge': 1.0 - buy_sum,
            'buy_both_top_size': min(ask_size_a, ask_size_b),
            'sell_both_proceeds': sell_sum,
            'sell_both_gross_edge': sell_sum - 1.0,
            'sell_both_top_size': min(bid_size_a, bid_size_b)
        })

print('PAIR_COUNT', len(rows))
if not rows:
    raise SystemExit('no_binary_pairs')

buy_pos = [r for r in rows if r['buy_both_gross_edge'] > 0]
sell_pos = [r for r in rows if r['sell_both_gross_edge'] > 0]
print('BUY_BOTH_GROSS_POSITIVE', len(buy_pos))
print('SELL_BOTH_GROSS_POSITIVE', len(sell_pos))
print('BEST_BUY_BOTH_EDGE', max(r['buy_both_gross_edge'] for r in rows))
print('BEST_SELL_BOTH_EDGE', max(r['sell_both_gross_edge'] for r in rows))

for r in sorted(rows, key=lambda x: x['buy_both_gross_edge'], reverse=True)[:10]:
    print('PAIR', str(r['question'])[:160])
    print('OUTCOMES', r['outcomes'])
    print('BUY_COST', r['buy_both_cost'], 'BUY_EDGE', r['buy_both_gross_edge'], 'SIZE', r['buy_both_top_size'])
    print('SELL_PROCEEDS', r['sell_both_proceeds'], 'SELL_EDGE', r['sell_both_gross_edge'], 'SIZE', r['sell_both_top_size'])

print('POLYMARKET_COMPLEMENT_TEST_PASS')
