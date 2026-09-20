from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone
import json
import math

root=Path.cwd()
base=root/'knowledge/raw/market_rules/polymarket'
left_files=sorted(base.glob('*event-197776.json'),key=lambda p:p.stat().st_mtime)
right_files=sorted(base.glob('*event-428957.json'),key=lambda p:p.stat().st_mtime)
if not left_files or not right_files:
    raise SystemExit('rule_snapshot_missing')
left=json.loads(left_files[-1].read_text(encoding='utf-8'))
right=json.loads(right_files[-1].read_text(encoding='utf-8'))

wanted={'1328019','1328020','2110748','2110754'}
markets=dict()
for event in [left,right]:
    for market in event.get('markets') or tuple():
        if not isinstance(market,dict):
            continue
        mid=str(market.get('id') or '')
        if mid in wanted:
            markets[mid]=market
if set(markets)!=wanted:
    raise SystemExit('required_markets_missing')

def token_pair(market):
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
request_rows=list()
for mid in sorted(markets):
    pair=token_pair(markets.get(mid))
    tokenmap[mid]=pair
    request_rows.append(dict(token_id=pair.get('yes')))
    request_rows.append(dict(token_id=pair.get('no')))

url='https:'+chr(47)+chr(47)+'clob.polymarket.com/books'
body=json.dumps(request_rows).encode('utf-8')
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

def schedule(mid):
    market=markets.get(mid) or dict()
    fee=market.get('feeSchedule') or dict()
    return dict(enabled=market.get('feesEnabled'),rate=fee.get('rate'),exponent=fee.get('exponent'),takerOnly=fee.get('takerOnly'))

def make_leg(mid,side):
    token=(tokenmap.get(mid) or dict()).get(side)
    book=top(token)
    if not isinstance(book,dict) or book.get('ask') is None or book.get('ask_size') is None:
        raise SystemExit('missing_executable_ask')
    return dict(market_id=mid,side=side,token=token,ask=float(book.get('ask')),ask_size=float(book.get('ask_size')),fee=schedule(mid))

def taker_fee(size,item):
    fee=item.get('fee') or dict()
    if fee.get('enabled') is False:
        return 0.0
    if fee.get('enabled') is not True:
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

def evaluate(name,payout,legs):
    size=min(float(item.get('ask_size')) for item in legs)
    ask_sum=sum(float(item.get('ask')) for item in legs)
    gross_per=payout-ask_sum
    fees=list()
    known=True
    for item in legs:
        value=taker_fee(size,item)
        if value is None:
            known=False
        fees.append(value)
    fee_total=sum(value for value in fees if value is not None)
    gross_total=math.prod((gross_per,size))
    net=None
    capital=None
    roi=None
    if known:
        net=gross_total-fee_total
        capital=math.prod((ask_sum,size))+fee_total
        roi=net/capital if capital>0 else None
    return dict(name=name,guaranteed_payout_per_set=payout,common_size=size,ask_sum=ask_sum,gross_per_set=gross_per,gross_total=gross_total,fee_known=known,taker_fees_total=(fee_total if known else None),net_total=net,capital=capital,net_roi=roi,legs=legs)

paths=list()
paths.append(evaluate('NO_IPO_DUPLICATE_YES_LOWER_PLUS_NO_MIDDLE',1.0,[make_leg('1328020','yes'),make_leg('2110754','no')]))
paths.append(evaluate('NO_IPO_DUPLICATE_NO_LOWER_PLUS_YES_MIDDLE',1.0,[make_leg('1328020','no'),make_leg('2110754','yes')]))
paths.append(evaluate('BOUNDARY_TRIPLET_WITH_MIDDLE_NO_IPO',1.0,[make_leg('1328019','yes'),make_leg('2110748','yes'),make_leg('2110754','yes')]))
paths.append(evaluate('BOUNDARY_TRIPLET_WITH_LOWER_NO_IPO',1.0,[make_leg('1328019','yes'),make_leg('2110748','yes'),make_leg('1328020','yes')]))

stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
outdir=root/'knowledge/raw/market_data/polymarket_cross_series'
outdir.mkdir(parents=True,exist_ok=True)
out=outdir/(stamp+'-anthropic-197776-428957.json')
payload=dict(retrieved_at=datetime.now(timezone.utc).isoformat(),http_status=status,event_ids=['197776','428957'],formal_statewise_proof_e393=True,live_trading=False,paid_actions=False,wallet_actions=False,paths=paths,books=books)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')

print('HTTP_STATUS',status)
print('BOOK_COUNT',len(books))
for mid in sorted(markets):
    market=markets.get(mid) or dict()
    print('MARKET',mid,market.get('groupItemTitle'))
    print('YES_TOP',top((tokenmap.get(mid) or dict()).get('yes')))
    print('NO_TOP',top((tokenmap.get(mid) or dict()).get('no')))
    print('FEE_SCHEDULE',schedule(mid))
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
print('ANTHROPIC_CROSS_SERIES_PRICING_PASS')
