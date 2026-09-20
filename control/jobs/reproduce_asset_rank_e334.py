from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone
import json
import math

root=Path.cwd()
old_path=root/'knowledge/raw/market_data/polymarket_neg_risk_partial/20260920T013900Z106981.json'
if not old_path.exists():
    raise SystemExit('baseline_missing')
old=json.loads(old_path.read_text(encoding='utf-8'))
markets=old.get('markets') or tuple()
if len(markets)!=3:
    raise SystemExit('market_count_wrong')

tokens=list()
for market in markets:
    tokens.append(dict(token_id=str(market.get('yes_token'))))
    tokens.append(dict(token_id=str(market.get('no_token'))))

url='https:'+chr(47)+chr(47)+'clob.polymarket.com/books'
body=json.dumps(tokens).encode('utf-8')
req=Request(url,data=body,headers={'Content-Type':'application/json','User-Agent':'PredictionEdgeHunter/1.0'},method='POST')
with urlopen(req,timeout=30) as r:
    books=json.loads(r.read())
    status=r.status
bookmap=dict((str(book.get('asset_id')),book) for book in books)

def top(token):
    book=bookmap.get(str(token)) or dict()
    bids=book.get('bids') or tuple()
    asks=book.get('asks') or tuple()
    if not bids or not asks:
        raise SystemExit('two_sided_book_missing')
    bid=max(bids,key=lambda x:float(x.get('price',0)))
    ask=min(asks,key=lambda x:float(x.get('price',9)))
    return dict(bid=float(bid.get('price')),bid_size=float(bid.get('size',0)),ask=float(ask.get('price')),ask_size=float(ask.get('size',0)))

rows=list()
for market in markets:
    rows.append(dict(market_id=str(market.get('market_id')),question=str(market.get('question') or ''),yes=top(market.get('yes_token')),no=top(market.get('no_token'))))

ask_sum=sum((row.get('yes') or dict()).get('ask') for row in rows)
gross_per_set=1.0-ask_sum
common_size=min(float((row.get('yes') or dict()).get('ask_size')) for row in rows)
print('SECOND_TIMEPOINT_ASK_SUM',ask_sum)
print('SECOND_TIMEPOINT_GROSS_PER_SET',gross_per_set)
print('SECOND_TIMEPOINT_COMMON_SIZE',common_size)

best_conditional=-999.0
for i,row in enumerate(rows):
    y=row.get('yes') or dict()
    maker_price=float(y.get('bid'))
    queue=float(y.get('bid_size'))
    hedge_cost=0.0
    hedge_fees=0.0
    hedge_depths=list()
    for j,other in enumerate(rows):
        if j==i:
            continue
        oy=other.get('yes') or dict()
        p=float(oy.get('ask'))
        hedge_cost+=p
        hedge_depths.append(float(oy.get('ask_size')))
        hedge_fees+=round(math.prod((5.0,0.04,p,1.0-p)),5)
    gross_after_fill=1.0-maker_price-hedge_cost
    net_total=math.prod((gross_after_fill,5.0))-hedge_fees
    net_per_set=net_total/5.0
    best_conditional=max(best_conditional,net_per_set)
    print('MAKER_LEG',row.get('market_id'))
    print('BID',maker_price)
    print('ASK',y.get('ask'))
    print('QUEUE_AT_BID',queue)
    print('HEDGE_COST',hedge_cost)
    print('HEDGE_DEPTH',min(hedge_depths))
    print('CONDITIONAL_NET_PER_SET',net_per_set)

stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
outdir=root/'knowledge/raw/market_data/polymarket_neg_risk_partial'
out=outdir/(stamp+'106981_reproduction.json')
payload=dict(retrieved_at=datetime.now(timezone.utc).isoformat(),event_id='106981',http_status=status,live_trading=False,paid_actions=False,wallet_actions=False,rows=rows,yes_ask_sum=ask_sum,gross_per_set=gross_per_set,common_size=common_size,best_conditional_maker_net_per_set=best_conditional)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')

print('BEST_CONDITIONAL_MAKER_NET_PER_SET',best_conditional)
if gross_per_set>0 and best_conditional>0:
    print('REPRODUCTION_RESULT','STRUCTURE_PERSISTS_SECOND_TIMEPOINT')
elif best_conditional>0:
    print('REPRODUCTION_RESULT','MAKER_PATH_PERSISTS_WITHOUT_TAKER_BASKET_GROSS_EDGE')
else:
    print('REPRODUCTION_RESULT','CANDIDATE_DID_NOT_PERSIST')
print('PATH',out)
print('ASSET_SECOND_TIMEPOINT_REPRODUCTION_PASS')
