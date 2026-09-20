from pathlib import Path
import json
import math

root=Path.cwd()
price_path=root/'knowledge/raw/market_data/polymarket_neg_risk_partial/20260920T013900Z106981.json'
rule_path=root/'knowledge/raw/market_rules/polymarket/20260920T013931Zevent_106981.json'
if not price_path.exists():
    raise SystemExit('price_snapshot_missing')
if not rule_path.exists():
    raise SystemExit('rule_snapshot_missing')

snap=json.loads(price_path.read_text(encoding='utf-8'))
event=json.loads(rule_path.read_text(encoding='utf-8'))
rows=snap.get('priced') or tuple()
rules=event.get('markets') or tuple()
if len(rows)!=3 or len(rules)!=3:
    raise SystemExit('market_count_wrong')
if event.get('negRisk') is not True:
    raise SystemExit('event_not_neg_risk')
if event.get('negRiskAugmented') is not False:
    raise SystemExit('event_augmented')
if not event.get('negRiskMarketID'):
    raise SystemExit('group_missing')

rulemap=dict((str(row.get('id')),row) for row in rules)
for row in rows:
    mid=str(row.get('market_id'))
    rule=rulemap.get(mid) or dict()
    if rule.get('negRisk') is not True:
        raise SystemExit('market_not_neg_risk')
    if rule.get('negRiskOther') is not False:
        raise SystemExit('unexpected_other_flag')
    if rule.get('feesEnabled') is not True:
        raise SystemExit('fees_not_enabled')
    schedule=rule.get('feeSchedule') or dict()
    if float(schedule.get('rate') or 0)!=0.04:
        raise SystemExit('fee_rate_unexpected')
    if float(schedule.get('exponent') or 0)!=1.0:
        raise SystemExit('fee_exponent_unexpected')
    if schedule.get('takerOnly') is not True:
        raise SystemExit('taker_flag_unexpected')

for state in range(3):
    yes_total=0
    no_total=0
    for i in range(3):
        yes=1 if i==state else 0
        yes_total+=yes
        no_total+=1-yes
    if yes_total!=1 or no_total!=2:
        raise SystemExit('partition_proof_failed')
    for i in range(3):
        direct_no=0 if i==state else 1
        synth_no=0
        for j in range(3):
            if j!=i and j==state:
                synth_no+=1
        if direct_no!=synth_no:
            raise SystemExit('cross_rep_proof_failed')

size=min(float((row.get('yes') or dict()).get('ask_size')) for row in rows)
ask_sum=sum(float((row.get('yes') or dict()).get('ask')) for row in rows)
gross_per_set=1.0-ask_sum
fee_total=0.0
for row in rows:
    yes=row.get('yes') or dict()
    price=float(yes.get('ask'))
    fee=round(math.prod((size,0.04,price,1.0-price)),5)
    fee_total+=fee
    print('BASKET_LEG',row.get('market_id'),'ASK',price,'SIZE',yes.get('ask_size'),'FEE',fee)

gross_total=math.prod((gross_per_set,size))
net_total=gross_total-fee_total
capital=math.prod((ask_sum,size))+fee_total
roi=net_total/capital if capital>0 else 0

print('ASSET_STATEWISE_PROOF_PASS')
print('COMMON_SIZE',size)
print('YES_ASK_SUM',ask_sum)
print('GROSS_PER_SET',gross_per_set)
print('GROSS_TOTAL',gross_total)
print('TAKER_FEES_TOTAL',fee_total)
print('NET_TOTAL',net_total)
print('NET_ROI',roi)

best_gross=-999.0
best_net=-999.0
positive_gross=0
positive_net=0
for i,row in enumerate(rows):
    no=row.get('no') or dict()
    synth_cost=0.0
    synth_sizes=list()
    for j,other in enumerate(rows):
        if j==i:
            continue
        oy=other.get('yes') or dict()
        synth_cost+=float(oy.get('ask'))
        synth_sizes.append(float(oy.get('ask_size')))
    direct_bid=float(no.get('bid'))
    xsize=min(min(synth_sizes),float(no.get('bid_size')))
    gross=direct_bid-synth_cost
    fees=0.0
    for j,other in enumerate(rows):
        if j==i:
            continue
        p=float((other.get('yes') or dict()).get('ask'))
        fees+=round(math.prod((xsize,0.04,p,1.0-p)),5)
    fees+=round(math.prod((xsize,0.04,direct_bid,1.0-direct_bid)),5)
    net=math.prod((gross,xsize))-fees
    best_gross=max(best_gross,gross)
    best_net=max(best_net,net)
    if gross>0:
        positive_gross+=1
    if net>0:
        positive_net+=1
    print('IDENTITY',row.get('market_id'))
    print('QUESTION',row.get('question'))
    print('SYNTH_NO_ASK',synth_cost)
    print('DIRECT_NO_BID',direct_bid)
    print('GROSS_EDGE',gross)
    print('EXECUTABLE_SIZE',xsize)
    print('TAKER_FEES',fees)
    print('NET_AT_SIZE',net)

print('GROSS_POSITIVE_IDENTITIES',positive_gross)
print('NET_POSITIVE_IDENTITIES',positive_net)
print('BEST_GROSS_IDENTITY',best_gross)
print('BEST_NET_IDENTITY',best_net)
if net_total>0 or positive_net>0:
    print('RESULT','NET_CANDIDATE_SURVIVES_FEE_GATE')
elif gross_per_set>0 or positive_gross>0:
    print('RESULT','GROSS_EDGE_KILLED_BY_TAKER_FEES')
else:
    print('RESULT','NO_GROSS_EDGE')
print('ASSET_IDENTITY_FEE_TEST_PASS')
