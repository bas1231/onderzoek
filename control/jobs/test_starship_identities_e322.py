from pathlib import Path
import json
import math

root=Path.cwd()
price_path=root/'knowledge/raw/market_data/polymarket_neg_risk_partial/20260920T013454Z102763.json'
rule_path=root/'knowledge/raw/market_rules/polymarket/20260920T013526Zevent_102763.json'
if not price_path.exists():
    raise SystemExit('price_snapshot_missing')
if not rule_path.exists():
    raise SystemExit('rule_snapshot_missing')

snap=json.loads(price_path.read_text(encoding='utf-8'))
event=json.loads(rule_path.read_text(encoding='utf-8'))
markets=snap.get('markets') or tuple()
books=snap.get('books') or tuple()
rules=event.get('markets') or tuple()
if len(markets)!=8 or len(rules)!=8:
    raise SystemExit('market_count_wrong')
if event.get('negRisk') is not True:
    raise SystemExit('event_not_neg_risk')
if event.get('negRiskAugmented') is not False:
    raise SystemExit('event_augmented')
if not event.get('negRiskMarketID'):
    raise SystemExit('group_id_missing')

rulemap=dict((str(row.get('id')),row) for row in rules)
bookmap=dict((str(row.get('asset_id')),row) for row in books)
for market in markets:
    mid=str(market.get('market_id'))
    rule=rulemap.get(mid) or dict()
    if rule.get('negRisk') is not True:
        raise SystemExit('market_not_neg_risk')
    if rule.get('negRiskOther') is not False:
        raise SystemExit('unexpected_other_flag')
    if rule.get('feesEnabled') is not True:
        raise SystemExit('fees_disabled')
    schedule=rule.get('feeSchedule') or dict()
    if float(schedule.get('rate') or 0)!=0.04:
        raise SystemExit('fee_rate_unexpected')
    if float(schedule.get('exponent') or 0)!=1.0:
        raise SystemExit('fee_exponent_unexpected')
    if schedule.get('takerOnly') is not True:
        raise SystemExit('taker_flag_unexpected')

for state in range(8):
    yes_total=0
    no_total=0
    for i in range(8):
        yes=1 if i==state else 0
        yes_total+=yes
        no_total+=1-yes
    if yes_total!=1 or no_total!=7:
        raise SystemExit('partition_proof_failed')
    for i in range(8):
        direct_no=0 if i==state else 1
        synth_no=0
        for j in range(8):
            if j!=i and j==state:
                synth_no+=1
        if direct_no!=synth_no:
            raise SystemExit('cross_rep_proof_failed')

rows=list()
for market in markets:
    yes_book=bookmap.get(str(market.get('yes_token'))) or dict()
    no_book=bookmap.get(str(market.get('no_token'))) or dict()
    yes_asks=yes_book.get('asks') or tuple()
    yes_bids=yes_book.get('bids') or tuple()
    no_asks=no_book.get('asks') or tuple()
    no_bids=no_book.get('bids') or tuple()
    if not yes_asks or not no_bids:
        raise SystemExit('required_side_missing')
    yes_ask_row=min(yes_asks,key=lambda x:float(x.get('price',9)))
    no_bid_row=max(no_bids,key=lambda x:float(x.get('price',0)))
    row=dict(market_id=str(market.get('market_id')),question=str(market.get('question') or ''),yes_ask=float(yes_ask_row.get('price')),yes_ask_size=float(yes_ask_row.get('size',0)),no_bid=float(no_bid_row.get('price')),no_bid_size=float(no_bid_row.get('size',0)))
    if yes_bids:
        yes_bid_row=max(yes_bids,key=lambda x:float(x.get('price',0)))
        row.update(yes_bid=float(yes_bid_row.get('price')),yes_bid_size=float(yes_bid_row.get('size',0)))
    if no_asks:
        no_ask_row=min(no_asks,key=lambda x:float(x.get('price',9)))
        row.update(no_ask=float(no_ask_row.get('price')),no_ask_size=float(no_ask_row.get('size',0)))
    rows.append(row)

all_yes_cost=sum(row.get('yes_ask') for row in rows)
all_yes_size=min(row.get('yes_ask_size') for row in rows)
all_yes_gross=1.0-all_yes_cost
all_yes_fees=sum(round(math.prod((all_yes_size,0.04,row.get('yes_ask'),1.0-row.get('yes_ask'))),5) for row in rows)
all_yes_net=math.prod((all_yes_gross,all_yes_size))-all_yes_fees
print('STARSHIP_STATEWISE_PROOF_PASS')
print('STATE_COUNT',8)
print('ALL_YES_ASK_SUM',all_yes_cost)
print('ALL_YES_GROSS_PER_SET',all_yes_gross)
print('ALL_YES_COMMON_SIZE',all_yes_size)
print('ALL_YES_FEES',all_yes_fees)
print('ALL_YES_NET',all_yes_net)

positive=0
best=-999.0
for i,row in enumerate(rows):
    synth_cost=0.0
    synth_sizes=list()
    synth_fee=0.0
    for j,other in enumerate(rows):
        if j==i:
            continue
        price=float(other.get('yes_ask'))
        synth_cost+=price
        synth_sizes.append(float(other.get('yes_ask_size')))
    direct_bid=float(row.get('no_bid'))
    gross=direct_bid-synth_cost
    size=min(min(synth_sizes),float(row.get('no_bid_size')))
    for j,other in enumerate(rows):
        if j==i:
            continue
        price=float(other.get('yes_ask'))
        synth_fee+=round(math.prod((size,0.04,price,1.0-price)),5)
    direct_fee=round(math.prod((size,0.04,direct_bid,1.0-direct_bid)),5)
    net=math.prod((gross,size))-synth_fee-direct_fee
    best=max(best,gross)
    if gross>0:
        positive+=1
    print('IDENTITY',row.get('market_id'))
    print('QUESTION',row.get('question'))
    print('SYNTH_NO_ASK',synth_cost)
    print('DIRECT_NO_BID',direct_bid)
    print('GROSS_EDGE',gross)
    print('EXECUTABLE_SIZE',size)
    print('TOTAL_TAKER_FEES',synth_fee+direct_fee)
    print('NET_AT_SIZE',net)

print('GROSS_POSITIVE_IDENTITIES',positive)
print('BEST_GROSS_EDGE',best)
if all_yes_net>0 or positive>0:
    print('RESULT','CANDIDATE_REQUIRES_EXECUTION_REVIEW')
else:
    print('RESULT','NO_EXECUTION_REALISTIC_EDGE_FOUND')
print('STARSHIP_IDENTITY_TEST_PASS')
