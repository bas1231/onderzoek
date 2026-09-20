from pathlib import Path
import json
import math

root=Path.cwd()
book_path=root/'knowledge/raw/market_data/polymarket_neg_risk_partial/20260920T012324Z_51456.json'
rule_path=root/'knowledge/raw/market_rules/polymarket/20260920T012355Z_event_51456.json'
if not book_path.exists():
    raise SystemExit('book_snapshot_missing')
if not rule_path.exists():
    raise SystemExit('rule_snapshot_missing')

snap=json.loads(book_path.read_text(encoding='utf-8'))
event=json.loads(rule_path.read_text(encoding='utf-8'))
markets=snap.get('markets') or tuple()
books=snap.get('books') or tuple()
live=dict((str(row.get('id')),row) for row in (event.get('markets') or tuple()))
bookmap=dict((str(row.get('asset_id')),row) for row in books)
if len(markets)!=13:
    raise SystemExit('market_count_wrong')

size=75.0
ask_sum=0.0
fee_sum=0.0
for market in markets:
    mid=str(market.get('market_id'))
    rule=live.get(mid) or dict()
    schedule=rule.get('feeSchedule') or dict()
    enabled=rule.get('feesEnabled')
    rate=float(schedule.get('rate') or 0)
    exponent=float(schedule.get('exponent') or 0)
    taker_only=schedule.get('takerOnly')
    if enabled is not True:
        raise SystemExit('fees_not_enabled')
    if rate!=0.05:
        raise SystemExit('fee_rate_unexpected')
    if exponent!=1.0:
        raise SystemExit('fee_exponent_unexpected')
    if taker_only is not True:
        raise SystemExit('taker_flag_unexpected')
    token=str(market.get('yes_token'))
    book=bookmap.get(token) or dict()
    asks=book.get('asks') or tuple()
    if not asks:
        raise SystemExit('yes_ask_missing')
    ask=min(float(row.get('price')) for row in asks)
    top_size=sum(float(row.get('size',0)) for row in asks if float(row.get('price'))==ask)
    if top_size<size:
        raise SystemExit('top_size_below_test_size')
    fee=round(math.prod((size,rate,ask,1.0-ask)),5)
    ask_sum+=ask
    fee_sum+=fee
    print('LEG',mid,'ASK',ask,'TOP_SIZE',top_size,'FEE',fee)

gross_per_set=1.0-ask_sum
gross_total=math.prod((gross_per_set,size))
net_total=gross_total-fee_sum
net_per_set=net_total/size
capital=math.prod((ask_sum,size))+fee_sum
roi=net_total/capital if capital>0 else 0

print('LEG_COUNT',len(markets))
print('SIZE',size)
print('ASK_SUM',ask_sum)
print('GROSS_PER_SET',gross_per_set)
print('GROSS_TOTAL',gross_total)
print('TAKER_FEES_TOTAL',fee_sum)
print('NET_TOTAL',net_total)
print('NET_PER_SET',net_per_set)
print('CAPITAL_REQUIRED',capital)
print('NET_ROI',roi)
if net_total<=0:
    print('KILL_RESULT','KILLED_BY_TAKER_FEES')
elif net_total<0.05:
    print('KILL_RESULT','SURVIVES_BUT_TINY')
else:
    print('KILL_RESULT','SURVIVES_FEE_GATE')
print('FED_STORED_FEE_TEST_PASS')
