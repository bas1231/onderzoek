from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone
import hashlib
import json
import math

root=Path.cwd()
rule_dir=root/'knowledge/raw/market_rules/polymarket'
ids=['197776','428957','548858']
events=dict()
for eid in ids:
    candidates=list()
    for p in rule_dir.iterdir():
        if p.is_file() and p.name.endswith('event-'+eid+'.json'):
            candidates.append(p)
    candidates.sort(key=lambda p:p.stat().st_mtime)
    if not candidates:
        raise SystemExit('missing_event_'+eid)
    events[eid]=json.loads(candidates[-1].read_text(encoding='utf-8'))

base_desc=str(events['197776'].get('description') or '')
base_hash=hashlib.sha256(base_desc.encode()).hexdigest()
for eid in ids:
    event=events[eid]
    if str(event.get('description') or '')!=base_desc:
        raise SystemExit('event_rule_text_mismatch_'+eid)
    for market in event.get('markets') or tuple():
        if isinstance(market,dict) and str(market.get('description') or '')!=base_desc:
            raise SystemExit('market_rule_text_mismatch_'+str(market.get('id')))

markets=dict()
for eid in ids:
    for market in events[eid].get('markets') or tuple():
        if isinstance(market,dict):
            markets[str(market.get('id') or '')]=market

def token_pair(market):
    ids_raw=market.get('clobTokenIds')
    outs=market.get('outcomes')
    if isinstance(ids_raw,str):
        ids_raw=json.loads(ids_raw)
    if isinstance(outs,str):
        outs=json.loads(outs)
    if not isinstance(ids_raw,list) or not isinstance(outs,list) or len(ids_raw)!=2 or len(outs)!=2:
        raise SystemExit('token_shape_bad_'+str(market.get('id')))
    names=[str(value).lower() for value in outs]
    if 'yes' not in names or 'no' not in names:
        raise SystemExit('outcome_shape_bad_'+str(market.get('id')))
    return dict(yes=str(ids_raw[names.index('yes')]),no=str(ids_raw[names.index('no')]))

middle_low=['2110748','2110749','2110750','2110751']
middle_high=['2110752','2110753']
third_low=['2412744','2412745']
third_high=['2412746','2412747','2412748','2412749','2412750','2412751','2412752']
noipo=['1328020','2110754','2412753']
required=set(middle_low+middle_high+third_low+third_high+noipo)
for mid in required:
    if mid not in markets:
        raise SystemExit('required_market_missing_'+mid)

tokenmap=dict()
request_rows=list()
for mid in sorted(required):
    pair=token_pair(markets[mid])
    tokenmap[mid]=pair
    request_rows.append(dict(token_id=pair.get('yes')))
    request_rows.append(dict(token_id=pair.get('no')))

url='https:'+chr(47)+chr(47)+'clob.polymarket.com/books'
body=json.dumps(request_rows).encode()
req=Request(url,data=body,headers={'User-Agent':'PredictionEdgeHunter/1.0','Content-Type':'application/json'},method='POST')
with urlopen(req,timeout=40) as response:
    raw=response.read()
    status=response.status
books=json.loads(raw)
if not isinstance(books,list):
    raise SystemExit('books_shape_bad')
bookmap=dict((str(book.get('asset_id')),book) for book in books if isinstance(book,dict))

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
    market=markets[mid]
    fee=market.get('feeSchedule') or dict()
    return dict(enabled=market.get('feesEnabled'),rate=fee.get('rate'),exponent=fee.get('exponent'),takerOnly=fee.get('takerOnly'))

def leg(mid,side):
    token=(tokenmap.get(mid) or dict()).get(side)
    book=top(token)
    if not isinstance(book,dict) or book.get('ask') is None or book.get('ask_size') is None:
        raise SystemExit('missing_executable_ask_'+mid+''+side)
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

def price_path(name,legs,payout=1.0):
    size=min(float(item.get('ask_size')) for item in legs)
    ask_sum=sum(float(item.get('ask')) for item in legs)
    gross_per=payout-ask_sum
    gross_total=math.prod((gross_per,size))
    fees=list()
    known=True
    for item in legs:
        value=taker_fee(size,item)
        if value is None:
            known=False
        else:
            fees.append(value)
    fee_total=sum(fees)
    net=None
    capital=None
    roi=None
    if known:
        net=gross_total-fee_total
        capital=math.prod((ask_sum,size))+fee_total
        if capital>0:
            roi=net/capital
    return dict(name=name,guaranteed_payout_per_set=payout,common_size=size,ask_sum=ask_sum,gross_per_set=gross_per,gross_total=gross_total,fee_known=known,taker_fees_total=(fee_total if known else None),net_total=net,capital=capital,net_roi=roi,legs=legs)

paths=list()
labels={'1328020':'LOWER_NOIPO','2110754':'MIDDLE_NOIPO','2412753':'THIRD_NOIPO'}
for left in noipo:
    for right in noipo:
        if left==right:
            continue
        paths.append(price_path('DIRECT'+labels[left]+'YES_PLUS'+labels[right]+'NO',[leg(left,'yes'),leg(right,'no')]))

for no_mid in noipo:
    legs_a=[leg(mid,'yes') for mid in middle_high]+[leg(mid,'yes') for mid in third_low]+[leg(no_mid,'yes')]
    paths.append(price_path('LOCK_MIDDLE_GE_1_5_PLUS_THIRD_LT_1_5_PLUS'+labels[no_mid],legs_a))
    legs_b=[leg(mid,'yes') for mid in third_high]+[leg(mid,'yes') for mid in middle_low]+[leg(no_mid,'yes')]
    paths.append(price_path('LOCK_THIRD_GE_1_5_PLUS_MIDDLE_LT_1_5_PLUS_'+labels[no_mid],legs_b))

stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
outdir=root/'knowledge/raw/market_data/polymarket_cross_series'
outdir.mkdir(parents=True,exist_ok=True)
out=outdir/(stamp+'-anthropic-197776-428957-548858.json')
payload=dict(retrieved_at=datetime.now(timezone.utc).isoformat(),http_status=status,event_ids=ids,formal_rule_text_identity_e408=True,rule_description_sha256=base_hash,metadata_enddate_mismatch=True,live_trading=False,paid_actions=False,wallet_actions=False,paths=paths,books=books)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')

print('HTTP_STATUS',status)
print('BOOK_COUNT',len(books))
print('RULE_DESCRIPTION_SHA256',base_hash)
print('METADATA_ENDDATE_MISMATCH',True)
for mid in noipo+middle_high+third_low:
    print('MARKET',mid,'QUESTION',str(markets[mid].get('question') or ''))
    print('YES_TOP',top((tokenmap.get(mid) or dict()).get('yes')))
    print('NO_TOP',top((tokenmap.get(mid) or dict()).get('no')))
    print('FEE_SCHEDULE',schedule(mid))
for path in paths:
    print('PATH',path.get('name'))
    print('LEG_COUNT',len(path.get('legs') or tuple()))
    print('ASK_SUM',path.get('ask_sum'))
    print('COMMON_SIZE',path.get('common_size'))
    print('GROSS_PER_SET',path.get('gross_per_set'))
    print('GROSS_TOTAL',path.get('gross_total'))
    print('FEE_KNOWN',path.get('fee_known'))
    print('TAKER_FEES_TOTAL',path.get('taker_fees_total'))
    print('NET_TOTAL',path.get('net_total'))
    print('NET_ROI',path.get('net_roi'))
gross_positive=sum(1 for path in paths if float(path.get('gross_per_set') or 0)>0)
net_positive=sum(1 for path in paths if path.get('net_total') is not None and float(path.get('net_total'))>0)
print('PATH_COUNT',len(paths))
print('GROSS_POSITIVE_PATHS',gross_positive)
print('NET_POSITIVE_PATHS',net_positive)
print('SNAPSHOT_PATH',out)
print('ANTHROPIC_THREE_SERIES_PRICING_E410_PASS')
