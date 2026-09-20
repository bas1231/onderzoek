from pathlib import Path
from urllib.request import Request,urlopen
import json

root=Path.cwd()
snap_path=root/'knowledge/raw/market_data/polymarket_neg_risk_partial/20260920T012324Z_51456.json'
if not snap_path.exists():
    raise SystemExit('snapshot_missing')
snap=json.loads(snap_path.read_text(encoding='utf-8'))
markets=snap.get('markets') or tuple()
books=snap.get('books') or tuple()
if len(markets)!=13:
    raise SystemExit('market_count_wrong')
bookmap=dict((str(book.get('asset_id')),book) for book in books)

url='https:'+chr(47)+chr(47)+'gamma-api.polymarket.com/events/51456'
req=Request(url,headers={'User-Agent':'PredictionEdgeHunter/1.0'})
with urlopen(req,timeout=30) as r:
    event=json.loads(r.read())
current=dict((str(m.get('id')),m) for m in (event.get('markets') or tuple()))

size=75.0
ask_sum=0.0
fee_sum=0.0
leg_count=0
for market in markets:
    mid=str(market.get('market_id'))
    live=current.get(mid) or dict()
    schedule=live.get('feeSchedule') or dict()
    enabled=live.get('feesEnabled')
    rate=float(schedule.get('rate') or 0)
    exponent=float(schedule.get('exponent') or 0)
    taker_only=schedule.get('takerOnly')
    if enabled is not True or rate!=0.05 or exponent!=1.0 or taker_only is not True:
        raise SystemExit('fee_config_changed')
    token=str(market.get('yes_token'))
    book=bookmap.get(token) or dict()
    asks=book.get('asks') or tuple()
    if not asks:
        raise SystemExit('ask_missing')
    ask=min(float(x.get('price')) for x in asks)
    top_rows=[x for x in asks if float(x.get('price'))==ask]
    top_size=sum(float(x.get('size',0)) for x in top_rows)
    if top_size<size:
        raise SystemExit('top_size_below_75')
    fee=round(sizerateask*(1.0-ask),5)
    ask_sum+=ask
    fee_sum+=fee
    leg_count+=1
    print('LEG',mid,'ASK',ask,'TOP_SIZE',top_size,'FEE',fee)

gross_per_set=1.0-ask_sum
gross_total=gross_per_set*size
net_total=gross_total-fee_sum
net_per_set=net_total/size
print('LEG_COUNT',leg_count)
print('SIZE',size)
print('ASK_SUM',ask_sum)
print('GROSS_PER_SET',gross_per_set)
print('GROSS_TOTAL',gross_total)
print('TAKER_FEES_TOTAL',fee_sum)
print('NET_TOTAL',net_total)
print('NET_PER_SET',net_per_set)
if net_total<=0:
    print('KILL_RESULT','KILLED_BY_TAKER_FEES')
elif net_total<0.05:
    print('KILL_RESULT','SURVIVES_BUT_ECONOMICALLY_NEGLIGIBLE')
else:
    print('KILL_RESULT','SURVIVES_FEE_GATE')
print('FED_NET_EDGE_TEST_PASS')
