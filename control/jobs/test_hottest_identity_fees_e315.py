from pathlib import Path
import json
import math

root=Path.cwd()
price_path=root/'knowledge/raw/market_data/polymarket_neg_risk/20260920T013043Z79905.json'
rule_path=root/'knowledge/raw/market_rules/polymarket/20260920T013119Zevent_79905.json'
if not price_path.exists():
    raise SystemExit('price_snapshot_missing')
if not rule_path.exists():
    raise SystemExit('rule_snapshot_missing')

prices=json.loads(price_path.read_text(encoding='utf-8'))
event=json.loads(rule_path.read_text(encoding='utf-8'))
rows=prices.get('priced') or tuple()
rules=event.get('markets') or tuple()
if len(rows)!=6 or len(rules)!=6:
    raise SystemExit('market_count_wrong')

expected={'678686','678687','678688','678689','678690','678691'}
seen=set(str(row.get('market_id')) for row in rows)
if seen!=expected:
    raise SystemExit('unexpected_market_ids')

for state in range(6):
    yes_total=0
    no_total=0
    for i in range(6):
        yes=1 if i==state else 0
        yes_total+=yes
        no_total+=1-yes
    if yes_total!=1 or no_total!=5:
        raise SystemExit('statewise_partition_failed')
    for i in range(6):
        direct_no=0 if i==state else 1
        synth_no=0
        for j in range(6):
            if j!=i and j==state:
                synth_no+=1
        if direct_no!=synth_no:
            raise SystemExit('cross_representation_failed')

rulemap=dict((str(row.get('id')),row) for row in rules)
for row in rows:
    mid=str(row.get('market_id'))
    rule=rulemap.get(mid) or dict()
    if rule.get('negRisk') is not True:
        raise SystemExit('neg_risk_missing')
    if rule.get('negRiskOther') is not False:
        raise SystemExit('neg_risk_other_unexpected')
    if rule.get('feesEnabled') is not True:
        raise SystemExit('fees_not_enabled')
    schedule=rule.get('feeSchedule') or dict()
    if float(schedule.get('rate') or 0)!=0.05:
        raise SystemExit('fee_rate_unexpected')
    if float(schedule.get('exponent') or 0)!=1.0:
        raise SystemExit('fee_exponent_unexpected')
    if schedule.get('takerOnly') is not True:
        raise SystemExit('taker_flag_unexpected')

sizes=list()
for row in rows:
    yes=row.get('yes') or dict()
    if yes.get('ask') is None or yes.get('ask_size') is None:
        raise SystemExit('yes_top_missing')
    sizes.append(float(yes.get('ask_size')))
size=min(sizes)
if size<5:
    raise SystemExit('common_size_below_minimum')

ask_sum=0.0
fee_sum=0.0
for row in rows:
    mid=str(row.get('market_id'))
    yes=row.get('yes') or dict()
    price=float(yes.get('ask'))
    ask_size=float(yes.get('ask_size'))
    fee=round(math.prod((size,0.05,price,1.0-price)),5)
    ask_sum+=price
    fee_sum+=fee
    print('LEG',mid,'ASK',price,'ASK_SIZE',ask_size,'FEE',fee)

gross_per_set=1.0-ask_sum
gross_total=math.prod((gross_per_set,size))
net_total=gross_total-fee_sum
net_per_set=net_total/size
capital=math.prod((ask_sum,size))+fee_sum
roi=net_total/capital if capital>0 else 0

print('HOTTEST_STATEWISE_PROOF_PASS')
print('STATE_COUNT',6)
print('COMMON_TOP_SIZE',size)
print('ASK_SUM',ask_sum)
print('GROSS_PER_SET',gross_per_set)
print('GROSS_TOTAL',gross_total)
print('TAKER_FEES_TOTAL',fee_sum)
print('NET_TOTAL',net_total)
print('NET_PER_SET',net_per_set)
print('CAPITAL_REQUIRED',capital)
print('NET_ROI',roi)
print('FEE_PROVENANCE','NEAR_POINT_IN_TIME_36_SECONDS')
if net_total<=0:
    print('KILL_RESULT','KILLED_BY_TAKER_FEES')
elif net_total<0.05:
    print('KILL_RESULT','POSITIVE_BUT_ECONOMICALLY_NEGLIGIBLE')
else:
    print('KILL_RESULT','SURVIVES_FEE_GATE')
print('HOTTEST_IDENTITY_FEE_TEST_PASS')
