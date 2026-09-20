from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone
import json
import math

root=Path.cwd()
rules=root/'knowledge/raw/market_rules/polymarket'
left_files=sorted(rules.glob('*event-178817.json'),key=lambda p:p.stat().st_mtime)
right_files=sorted(rules.glob('*event-189770.json'),key=lambda p:p.stat().st_mtime)
if not left_files or not right_files:
    raise SystemExit('rule_snapshot_missing')
left=json.loads(left_files[-1].read_text(encoding='utf-8'))
right=json.loads(right_files[-1].read_text(encoding='utf-8'))

wanted={'1234161','1273048','1273050','1273051','1273052','1273053','1273054'}
markets=dict()
for event in [left,right]:
    for market in event.get('markets') or tuple():
        mid=str(market.get('id') or '')
        if mid in wanted:
            markets[mid]=market
if set(markets)!=wanted:
    raise SystemExit('required_markets_missing')

def tokens(market):
    ids=market.get('clobTokenIds')
    outs=market.get('outcomes')
    if isinstance(ids,str):
        ids=json.loads(ids)
    if isinstance(outs,str):
        outs=json.loads(outs)
    if not isinstance(ids,list) or not isinstance(outs,list) or len(ids)!=2 or len(outs)!=2:
        raise SystemExit('token_shape_bad')
    names=[str(x).lower() for x in outs]
    if 'yes' not in names or 'no' not in names:
        raise SystemExit('binary_outcomes_missing')
    return dict(yes=str(ids[names.index('yes')]),no=str(ids[names.index('no')]))

tokenmap=dict()
requests=list()
for mid in sorted(markets):
    pair=tokens(markets.get(mid))
    tokenmap[mid]=pair
    requests.append(dict(token_id=pair.get('yes')))
    requests.append(dict(token_id=pair.get('no')))

url='https:'+chr(47)+chr(47)+'clob.polymarket.com/books'
body=json.dumps(requests).encode('utf-8')
req=Request(url,data=body,headers={'Content-Type':'application/json','User-Agent':'PredictionEdgeHunter/1.0'},method='POST')
with urlopen(req,timeout=30) as response:
    raw=response.read()
    status=response.status
books=json.loads(raw)
bookmap=dict((str(book.get('asset_id')),book) for book in books)

def top(token):
    book=bookmap.get(str(token))
    if not isinstance(book,dict):
        return None
    bids=book.get('bids') or tuple()
    asks=book.get('asks') or tuple()
    out=dict()
    if bids:
        bid=max(bids,key=lambda row:float(row.get('price',0)))
        out['bid']=float(bid.get('price'))
        out['bid_size']=float(bid.get('size',0))
    if asks:
        ask=min(asks,key=lambda row:float(row.get('price',9)))
        out['ask']=float(ask.get('price'))
        out['ask_size']=float(ask.get('size',0))
    return out

def fee_schedule(mid):
    market=markets.get(mid) or dict()
    enabled=market.get('feesEnabled')
    schedule=market.get('feeSchedule') or dict()
    return dict(enabled=enabled,rate=schedule.get('rate'),exponent=schedule.get('exponent'),takerOnly=schedule.get('takerOnly'))

def leg(mid,side):
    token=(tokenmap.get(mid) or dict()).get(side)
    book=top(token)
    if not isinstance(book,dict) or book.get('ask') is None or book.get('ask_size') is None:
        raise SystemExit('missing_executable_ask')
    return dict(market_id=mid,side=side,token=token,ask=float(book.get('ask')),ask_size=float(book.get('ask_size')),fee=fee_schedule(mid))

def fee_for(size,item):
    fee=item.get('fee') or dict()
    enabled=fee.get('enabled')
    if enabled is False:
        return 0.0
    if enabled is not True:
        return None
    try:
        rate=float(fee.get('rate'))
        exponent=float(fee.get('exponent'))
    except Exception:
        return None
    if exponent!=1.0 or fee.get('takerOnly') is not True:
        return None
    p=float(item.get('ask'))
    return round(math.prod((size,rate,p,1.0-p)),5)

def price_path(name,legs):
    size=min(float(item.get('ask_size')) for item in legs)
    ask_sum=sum(float(item.get('ask')) for item in legs)
    gross_per=1.0-ask_sum
    fees=list()
    fee_known=True
    for item in legs:
        value=fee_for(size,item)
        if value is None:
            fee_known=False
        fees.append(value)
    fee_total=sum(value for value in fees if value is not None)
    gross_total=math.prod((gross_per,size))
    net_total=None
    capital=None
    roi=None
    if fee_known:
        net_total=gross_total-fee_total
        capital=math.prod((ask_sum,size))+fee_total
        roi=net_total/capital if capital>0 else None
    return dict(name=name,guaranteed_payout_per_set=1.0,common_size=size,ask_sum=ask_sum,gross_per_set=gross_per,gross_total=gross_total,fee_known=fee_known,taker_fees_total=(fee_total if fee_known else None),net_total=net_total,capital=capital,net_roi=roi,legs=legs)

paths=list()
paths.append(price_path('CROSS_COMPLEMENT_YES',[leg('1234161','yes'),leg('1273048','yes')]))
paths.append(price_path('CROSS_COMPLEMENT_NO',[leg('1234161','no'),leg('1273048','no')]))
paths.append(price_path('CROSS_PARTITION_NO_A_PLUS_HIGHER_YES_B',[leg('1234161','no'),leg('1273050','yes'),leg('1273051','yes'),leg('1273052','yes'),leg('1273053','yes'),leg('1273054','yes')]))

stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
outdir=root/'knowledge/raw/market_data/polymarket_cross_series'
outdir.mkdir(parents=True,exist_ok=True)
out=outdir/(stamp+'-argentina-fx-178817-189770.json')
payload=dict(retrieved_at=datetime.now(timezone.utc).isoformat(),http_status=status,event_ids=['178817','189770'],rule_paths=[str(left_files[-1]),str(right_files[-1])],formal_identity_prerequisites_from_e383=True,live_trading=False,paid_actions=False,wallet_actions=False,paths=paths,books=books)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')

print('HTTP_STATUS',status)
print('BOOK_COUNT',len(books))
for mid in sorted(markets):
    print('MARKET',mid,markets.get(mid).get('groupItemTitle'))
    print('YES_TOP',top((tokenmap.get(mid) or dict()).get('yes')))
    print('NO_TOP',top((tokenmap.get(mid) or dict()).get('no')))
    print('FEE_SCHEDULE',fee_schedule(mid))
for path in paths:
    print('PATH_NAME',path.get('name'))
    print('COMMON_SIZE',path.get('common_size'))
    print('ASK_SUM',path.get('ask_sum'))
    print('GROSS_PER_SET',path.get('gross_per_set'))
    print('GROSS_TOTAL',path.get('gross_total'))
    print('FEE_KNOWN',path.get('fee_known'))
    print('TAKER_FEES_TOTAL',path.get('taker_fees_total'))
    print('NET_TOTAL',path.get('net_total'))
    print('NET_ROI',path.get('net_roi'))
    print('---')
positive=[path for path in paths if path.get('net_total') is not None and float(path.get('net_total'))>0]
gross=[path for path in paths if float(path.get('gross_total'))>0]
print('GROSS_POSITIVE_PATHS',len(gross))
print('NET_POSITIVE_PATHS',len(positive))
print('RESULT','NET_CANDIDATE_EXISTS' if positive else ('GROSS_ONLY_CANDIDATE' if gross else 'NO_GROSS_EDGE'))
print('SNAPSHOT_PATH',out)
print('ARGENTINA_FX_CROSS_SERIES_PRICING_PASS')
