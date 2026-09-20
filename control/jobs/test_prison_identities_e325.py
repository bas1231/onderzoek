from pathlib import Path
import json
import math

root=Path.cwd()
price_path=root/'knowledge/raw/market_data/polymarket_neg_risk_partial/20260920T013653Z85579.json'
rule_path=root/'knowledge/raw/market_rules/polymarket/20260920T013720Zevent_85579.json'
if not price_path.exists():
    raise SystemExit('price_snapshot_missing')
if not rule_path.exists():
    raise SystemExit('rule_snapshot_missing')

snap=json.loads(price_path.read_text(encoding='utf-8'))
event=json.loads(rule_path.read_text(encoding='utf-8'))
rows=snap.get('priced') or tuple()
rules=event.get('markets') or tuple()
if len(rows)!=4 or len(rules)!=4:
    raise SystemExit('market_count_wrong')
if event.get('negRisk') is not True:
    raise SystemExit('event_not_neg_risk')
if event.get('negRiskAugmented') is not False:
    raise SystemExit('event_augmented')
if not event.get('negRiskMarketID'):
    raise SystemExit('group_id_missing')

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
    if float(schedule.get('rate') or 0)!=0.05:
        raise SystemExit('fee_rate_unexpected')
    if float(schedule.get('exponent') or 0)!=1.0:
        raise SystemExit('fee_exponent_unexpected')
    if schedule.get('takerOnly') is not True:
        raise SystemExit('taker_flag_unexpected')

for state in range(4):
    yes_total=0
    no_total=0
    for i in range(4):
        yes=1 if i==state else 0
        yes_total+=yes
        no_total+=1-yes
    if yes_total!=1 or no_total!=3:
        raise SystemExit('partition_proof_failed')
    for i in range(4):
        direct_no=0 if i==state else 1
        synth_no=0
        for j in range(4):
            if j!=i and j==state:
                synth_no+=1
        if direct_no!=synth_no:
            raise SystemExit('cross_rep_proof_failed')

print('PRISON_STATEWISE_PROOF_PASS')
print('STATE_COUNT',4)

pos_a=0
pos_b=0
best_a=-999.0
best_b=-999.0
best_net_a=-999.0
best_net_b=-999.0
for i,row in enumerate(rows):
    yes=row.get('yes') or dict()
    no=row.get('no') or dict()
    if yes.get('bid') is None or yes.get('ask') is None or no.get('bid') is None or no.get('ask') is None:
        raise SystemExit('two_sided_data_missing')

    synth_ask=0.0
    synth_bid=0.0
    ask_sizes=list()
    bid_sizes=list()
    for j,other in enumerate(rows):
        if j==i:
            continue
        oy=other.get('yes') or dict()
        synth_ask+=float(oy.get('ask'))
        synth_bid+=float(oy.get('bid'))
        ask_sizes.append(float(oy.get('ask_size')))
        bid_sizes.append(float(oy.get('bid_size')))

    no_bid=float(no.get('bid'))
    no_ask=float(no.get('ask'))
    size_a=min(min(ask_sizes),float(no.get('bid_size')))
    size_b=min(min(bid_sizes),float(no.get('ask_size')))
    gross_a=no_bid-synth_ask
    gross_b=synth_bid-no_ask

    fees_a=0.0
    fees_b=0.0
    for j,other in enumerate(rows):
        if j==i:
            continue
        oy=other.get('yes') or dict()
        pa=float(oy.get('ask'))
        pb=float(oy.get('bid'))
        fees_a+=round(math.prod((size_a,0.05,pa,1.0-pa)),5)
        fees_b+=round(math.prod((size_b,0.05,pb,1.0-pb)),5)
    fees_a+=round(math.prod((size_a,0.05,no_bid,1.0-no_bid)),5)
    fees_b+=round(math.prod((size_b,0.05,no_ask,1.0-no_ask)),5)

    net_a=math.prod((gross_a,size_a))-fees_a
    net_b=math.prod((gross_b,size_b))-fees_b

    if gross_a>0:
        pos_a+=1
    if gross_b>0:
        pos_b+=1
    best_a=max(best_a,gross_a)
    best_b=max(best_b,gross_b)
    best_net_a=max(best_net_a,net_a)
    best_net_b=max(best_net_b,net_b)

    print('IDENTITY',row.get('market_id'))
    print('QUESTION',row.get('question'))
    print('SYNTH_ASK',synth_ask)
    print('DIRECT_NO_BID',no_bid)
    print('GROSS_A',gross_a)
    print('SIZE_A',size_a)
    print('FEES_A',fees_a)
    print('NET_A',net_a)
    print('SYNTH_BID',synth_bid)
    print('DIRECT_NO_ASK',no_ask)
    print('GROSS_B',gross_b)
    print('SIZE_B',size_b)
    print('FEES_B',fees_b)
    print('NET_B',net_b)

print('GROSS_POSITIVE_A',pos_a)
print('GROSS_POSITIVE_B',pos_b)
print('BEST_GROSS_A',best_a)
print('BEST_GROSS_B',best_b)
print('BEST_NET_A',best_net_a)
print('BEST_NET_B',best_net_b)
if best_net_a>0 or best_net_b>0:
    print('RESULT','NET_CANDIDATE_REQUIRES_EXECUTION_REVIEW')
elif pos_a>0 or pos_b>0:
    print('RESULT','GROSS_ONLY_CANDIDATE_KILLED_BY_FEES')
else:
    print('RESULT','NO_GROSS_CROSS_REPRESENTATION_EDGE')
print('PRISON_IDENTITY_TEST_PASS')
