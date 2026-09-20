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

rulemap=dict((str(row.get('id')),row) for row in rules)
for row in rows:
    rule=rulemap.get(str(row.get('market_id'))) or dict()
    schedule=rule.get('feeSchedule') or dict()
    if rule.get('feesEnabled') is not True:
        raise SystemExit('fees_not_enabled')
    if schedule.get('takerOnly') is not True:
        raise SystemExit('not_taker_only')
    if float(schedule.get('rate') or 0)!=0.04:
        raise SystemExit('unexpected_taker_rate')

shadow_size=5.0
best=-999.0
for i,row in enumerate(rows):
    yes=row.get('yes') or dict()
    maker_price=float(yes.get('bid'))
    maker_queue=float(yes.get('bid_size'))
    maker_ask=float(yes.get('ask'))
    tick=maker_ask-maker_price
    hedge_cost=0.0
    hedge_fees=0.0
    hedge_sizes=list()
    for j,other in enumerate(rows):
        if j==i:
            continue
        oy=other.get('yes') or dict()
        p=float(oy.get('ask'))
        hedge_cost+=p
        hedge_sizes.append(float(oy.get('ask_size')))
        hedge_fees+=round(math.prod((shadow_size,0.04,p,1.0-p)),5)
    total_price=maker_price+hedge_cost
    gross_per_set=1.0-total_price
    net_total=math.prod((gross_per_set,shadow_size))-hedge_fees
    net_per_set=net_total/shadow_size
    hedge_depth=min(hedge_sizes)
    best=max(best,net_per_set)
    print('MAKER_LEG',row.get('market_id'))
    print('QUESTION',row.get('question'))
    print('MAKER_BID',maker_price)
    print('MAKER_ASK',maker_ask)
    print('SPREAD',tick)
    print('QUEUE_AHEAD_AT_BEST_BID',maker_queue)
    print('SHADOW_SIZE',shadow_size)
    print('HEDGE_ASK_COST',hedge_cost)
    print('HEDGE_COMMON_DEPTH',hedge_depth)
    print('TOTAL_ENTRY_PRICE',total_price)
    print('GROSS_PER_SET_AFTER_FILL',gross_per_set)
    print('TAKER_HEDGE_FEES',hedge_fees)
    print('NET_TOTAL_AFTER_FILL',net_total)
    print('NET_PER_SET_AFTER_FILL',net_per_set)
    print('ONE_TICK_HEDGE_WORSE_NET_PER_SET',net_per_set-0.01)
    print('TWO_TICK_HEDGE_WORSE_NET_PER_SET',net_per_set-0.02)
    print('---')

print('BEST_CONDITIONAL_NET_PER_SET',best)
if best<=0:
    print('PREBUILD_RESULT','KILL_MAKER_HEDGE_PATH')
elif best<=0.01:
    print('PREBUILD_RESULT','MARGIN_TOO_THIN_FOR_PRIORITY')
else:
    print('PREBUILD_RESULT','SURVIVES_ARITHMETIC_ONLY_NEEDS_PROSPECTIVE_FILL_TEST')
print('MAKER_FILL_ASSUMPTION','UNPROVEN')
print('QUEUE_POSITION_ASSUMPTION','JOIN_BEHIND_DISPLAYED_BEST_BID')
print('ASSET_MAKER_HEDGE_PREBUILD_PASS')
