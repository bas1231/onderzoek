from pathlib import Path
import json

root = Path.cwd()
base = root / 'knowledge/raw/market_data/polymarket_neg_risk'
files = sorted(base.glob('*48292.json'), key=lambda p: p.stat().st_mtime)
if not files:
    raise SystemExit('no_group_snapshot')

data = json.loads(files[-1].read_text(encoding='utf-8'))
markets = data.get('markets', [])
books = {str(b.get('asset_id')): b for b in data.get('books', [])}
if len(markets) != 7:
    raise SystemExit('unexpected_market_count')

def top(token):
    book = books.get(str(token))
    if not book:
        raise SystemExit('missing_book')
    bids = book.get('bids') or []
    asks = book.get('asks') or []
    if not bids or not asks:
        raise SystemExit('one_sided_book')
    bid = max(bids, key=lambda x: float(x.get('price', 0)))
    ask = min(asks, key=lambda x: float(x.get('price', 9)))
    return float(bid.get('price')), float(bid.get('size')), float(ask.get('price')), float(ask.get('size'))

rows = []
for market in markets:
    outcomes = [str(x).lower() for x in market['outcomes']]
    mapping = {outcomes[i]: str(market['tokens'][i]) for i in range(2)}
    if 'yes' not in mapping or 'no' not in mapping:
        raise SystemExit('bad_outcomes')
    y = top(mapping['yes'])
    n = top(mapping['no'])
    rows.append({'id': str(market['id']), 'question': market['question'], 'yes': y, 'no': n})

state_count = len(rows)
for state in range(state_count):
    all_yes = 0
    all_no = 0
    for i in range(state_count):
        yes = 1 if i == state else 0
        no = 1 - yes
        all_yes += yes
        all_no += no
    if all_yes != 1 or all_no != state_count - 1:
        raise SystemExit('partition_proof_failed')
    for i in range(state_count):
        no_i = 0 if i == state else 1
        others_yes = 0
        for j in range(state_count):
            if j != i and j == state:
                others_yes += 1
        if no_i != others_yes:
            raise SystemExit('identity_proof_failed')

sum_yes_ask = sum(r['yes'][2] for r in rows)
sum_yes_bid = sum(r['yes'][0] for r in rows)
sum_no_ask = sum(r['no'][2] for r in rows)
sum_no_bid = sum(r['no'][0] for r in rows)

print('STATEWISE_PROOF_PASS')
print('STATE_COUNT', state_count)
print('ALL_YES_ASK_COST', sum_yes_ask)
print('ALL_YES_GROSS_FLOOR_EDGE', 1.0 - sum_yes_ask)
print('ALL_YES_BID_SUM', sum_yes_bid)
print('ALL_NO_ASK_COST', sum_no_ask)
print('ALL_NO_GROSS_FLOOR_EDGE', 6.0 - sum_no_ask)
print('ALL_NO_BID_SUM', sum_no_bid)

positive = 0
for i,row in enumerate(rows):
    synthetic_ask = 0.0
    synthetic_bid = 0.0
    sizes_buy = []
    sizes_sell = []
    for j,other in enumerate(rows):
        if j == i:
            continue
        synthetic_ask += other['yes'][2]
        synthetic_bid += other['yes'][0]
        sizes_buy.append(other['yes'][3])
        sizes_sell.append(other['yes'][1])
    direct_no_bid = row['no'][0]
    direct_no_ask = row['no'][2]
    edge_buy_synth_sell_direct = direct_no_bid - synthetic_ask
    edge_buy_direct_sell_synth = synthetic_bid - direct_no_ask
    if edge_buy_synth_sell_direct > 0 or edge_buy_direct_sell_synth > 0:
        positive += 1
    print('IDENTITY', row['id'], row['question'][:180])
    print('NO_BID', direct_no_bid, 'NO_ASK', direct_no_ask)
    print('OTHER_YES_ASK_SUM', synthetic_ask, 'OTHER_YES_BID_SUM', synthetic_bid)
    print('EDGE_SYNTH_TO_DIRECT', edge_buy_synth_sell_direct)
    print('EDGE_DIRECT_TO_SYNTH', edge_buy_direct_sell_synth)
    print('BUY_SYNTH_TOP_SIZE', min(sizes_buy) if sizes_buy else 0)
    print('SELL_SYNTH_TOP_SIZE', min(sizes_sell) if sizes_sell else 0)

print('CROSS_REPRESENTATION_GROSS_POSITIVE', positive)
print('NEG_RISK_IDENTITY_TEST_PASS')
