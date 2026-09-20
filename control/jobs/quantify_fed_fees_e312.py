from pathlib import Path
import json
import math

root=Path.cwd()
p=root/'knowledge/raw/market_data/polymarket_neg_risk_partial/20260920T012324Z_51456.json'
if not p.exists():
    raise SystemExit('snapshot_missing')
data=json.loads(p.read_text(encoding='utf-8'))
markets=data.get('markets') or tuple()
books=data.get('books') or tuple()
bookmap=dict((str(row.get('asset_id')),row) for row in books)
if len(markets)!=13:
    raise SystemExit('market_count_wrong')

rate=0.05
size=75.0
ask_sum=0.0
fee_sum=0.0
for market in markets:
    token=str(market.get('yes_token'))
    book=bookmap.get(token) or dict()
    asks=book.get('asks') or tuple()
    if not asks:
        raise SystemExit('ask_missing')
    price=min(float(row.get('price')) for row in asks)
    top_size=sum(float(row.get('size',0)) for row in asks if float(row.get('price'))==price)
    if top_size<size:
        raise SystemExit('insufficient_top_size')
    fee=round(math.prod((size,rate,price,1.0-price)),5)
    ask_sum+=price
    fee_sum+=fee
    print('LEG',market.get('market_id'),'PRICE',price,'SIZE',top_size,'FEE',fee)

gross_per_set=1.0-ask_sum
gross_total=math.prod((gross_per_set,size))
net_total=gross_total-fee_sum
net_per_set=net_total/size
capital=math.prod((ask_sum,size))+fee_sum
roi=net_total/capital

print('ASK_SUM',ask_sum)
print('GROSS_PER_SET',gross_per_set)
print('GROSS_TOTAL',gross_total)
print('FEE_TOTAL',fee_sum)
print('NET_TOTAL',net_total)
print('NET_PER_SET',net_per_set)
print('CAPITAL',capital)
print('NET_ROI',roi)
if net_total<=0:
    print('PROVISIONAL_RESULT','KILLED_BY_FEES')
elif net_total<0.05:
    print('PROVISIONAL_RESULT','POSITIVE_BUT_TINY')
else:
    print('PROVISIONAL_RESULT','SURVIVES_FEE_ARITHMETIC')
print('POINT_IN_TIME_FEE_PROVENANCE','PENDING')
print('FED_FEE_QUANTIFICATION_PASS')
