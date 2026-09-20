from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone
import hashlib
import json
import math

root=Path.cwd()
agent='PredictionEdgeHunter/1.0'
event_url='https:'+chr(47)+chr(47)+'gamma-api.polymarket.com/events/548858'
req=Request(event_url,headers={'User-Agent':agent})
with urlopen(req,timeout=30) as response:
    event_raw=response.read()
    event_status=response.status
if event_status!=200:
    raise SystemExit('event_fetch_failed')
event=json.loads(event_raw)
markets=[m for m in event.get('markets') or tuple() if isinstance(m,dict) and m.get('negRisk') is True]
if len(markets)!=10:
    raise SystemExit('unexpected_market_count')
if event.get('negRiskAugmented') is True:
    raise SystemExit('augmented_market')
if any(m.get('negRiskOther') is True for m in markets):
    raise SystemExit('neg_risk_other_present')

def parse_pair(market):
    ids_raw=market.get('clobTokenIds')
    outcomes=market.get('outcomes')
    if isinstance(ids_raw,str):
        ids_raw=json.loads(ids_raw)
    if isinstance(outcomes,str):
        outcomes=json.loads(outcomes)
    if not isinstance(ids_raw,list) or not isinstance(outcomes,list):
        raise SystemExit('token_shape_bad')
    names=[str(value).lower() for value in outcomes]
    if 'yes' not in names or 'no' not in names:
        raise SystemExit('outcome_shape_bad')
    return str(ids_raw[names.index('yes')]),str(ids_raw[names.index('no')])

legs=list()
request_rows=list()
for market in markets:
    yes_token,no_token=parse_pair(market)
    fee=market.get('feeSchedule') or dict()
    if market.get('feesEnabled') is not True:
        raise SystemExit('fees_not_enabled_'+str(market.get('id')))
    if float(fee.get('exponent'))!=1.0 or fee.get('takerOnly') is not True:
        raise SystemExit('unsupported_fee_schedule_'+str(market.get('id')))
    leg=dict(market_id=str(market.get('id') or ''),label=str(market.get('groupItemTitle') or ''),question=str(market.get('question') or ''),no_token=no_token,fee_rate=float(fee.get('rate')))
    legs.append(leg)
    request_rows.append(dict(token_id=no_token))

books_url='https:'+chr(47)+chr(47)+'clob.polymarket.com/books'
body=json.dumps(request_rows).encode()
req=Request(books_url,data=body,headers={'User-Agent':agent,'Content-Type':'application/json'},method='POST')
with urlopen(req,timeout=40) as response:
    books_raw=response.read()
    books_status=response.status
if books_status!=200:
    raise SystemExit('books_fetch_failed')
books=json.loads(books_raw)
if not isinstance(books,list):
    raise SystemExit('books_shape_bad')
bookmap=dict((str(book.get('asset_id')),book) for book in books if isinstance(book,dict))

raw_dir=Path.home()/'.local/state/prediction-research/raw/polymarket_clob_books'
raw_dir.mkdir(parents=True,exist_ok=True)
books_sha=hashlib.sha256(books_raw).hexdigest()
books_path=raw_dir/(books_sha+'.json')
if not books_path.exists():
    books_path.write_bytes(books_raw)

for leg in legs:
    book=bookmap.get(str(leg.get('no_token')))
    if not isinstance(book,dict):
        raise SystemExit('missing_book_'+str(leg.get('market_id')))
    asks=book.get('asks') or tuple()
    if not asks:
        raise SystemExit('missing_ask_'+str(leg.get('market_id')))
    top=min(asks,key=lambda row:float(row.get('price',9)))
    leg['ask']=float(top.get('price'))
    leg['ask_size']=float(top.get('size',0))
    tick_raw=book.get('tick_size')
    if tick_raw is None:
        tick_raw=book.get('minimum_tick_size')
    leg['tick']=float(tick_raw) if tick_raw is not None else 0.001
    print('LEG',leg.get('market_id'),'LABEL',leg.get('label'),'NO_ASK',leg.get('ask'),'NO_ASK_SIZE',leg.get('ask_size'),'FEE_RATE',leg.get('fee_rate'),'TICK',leg.get('tick'))

conversion_fee_bips=0
question_count=10
collateral_multiplier=question_count-1

def received_shares(gross_quantity,price,rate):
    fee_usdc=round(math.prod((gross_quantity,rate,price,1.0-price)),5)
    fee_shares=fee_usdc/price
    return gross_quantity-fee_shares,fee_usdc,fee_shares

fixed_gross=5.0
fixed_cost=0.0
fixed_received=list()
fixed_depth_ok=True
for leg in legs:
    p=float(leg.get('ask'))
    depth=float(leg.get('ask_size'))
    if depth<fixed_gross:
        fixed_depth_ok=False
    received,fee_usdc,fee_shares=received_shares(fixed_gross,p,float(leg.get('fee_rate')))
    fixed_cost+=math.prod((fixed_gross,p))
    fixed_received.append(received)
    leg['fixed_gross_5_received_no']=received
    leg['fixed_gross_5_fee_usdc_equivalent']=fee_usdc
    leg['fixed_gross_5_fee_shares']=fee_shares
fixed_convertible=min(fixed_received)
fixed_collateral=math.prod((float(collateral_multiplier),fixed_convertible))
fixed_profit=fixed_collateral-fixed_cost
fixed_roi=fixed_profit/fixed_cost if fixed_cost>0 else None

print('FIXED_GROSS_SIZE',fixed_gross)
print('FIXED_ALL_DEPTH_OK',fixed_depth_ok)
print('FIXED_TOTAL_PURCHASE_COST',fixed_cost)
print('FIXED_MIN_NET_NO_SHARES',fixed_convertible)
print('FIXED_COLLATERAL_OUT',fixed_collateral)
print('FIXED_CONSERVATIVE_IMMEDIATE_PROFIT',fixed_profit)
print('FIXED_CONSERVATIVE_ROI',fixed_roi)
print('FIXED_PROFIT_POSITIVE',fixed_profit>0 and fixed_depth_ok)

target=5.0
optimized_cost=0.0
optimized_depth_ok=True
optimized_rows=list()
for leg in legs:
    p=float(leg.get('ask'))
    rate=float(leg.get('fee_rate'))
    factor=1.0-math.prod((rate,1.0-p))
    if factor<=0:
        raise SystemExit('bad_fee_factor')
    low=target
    high=target/factor+0.01
    for iteration in range(80):
        mid=(low+high)/2.0
        received,fee_usdc,fee_shares=received_shares(mid,p,rate)
        if received>=target:
            high=mid
        else:
            low=mid
    gross=high
    received,fee_usdc,fee_shares=received_shares(gross,p,rate)
    depth=float(leg.get('ask_size'))
    enough=depth>=gross
    if not enough:
        optimized_depth_ok=False
    cost=math.prod((gross,p))
    optimized_cost+=cost
    optimized_rows.append(dict(market_id=leg.get('market_id'),label=leg.get('label'),price=p,top_size=depth,gross_needed=gross,net_received=received,fee_usdc_equivalent=fee_usdc,fee_shares=fee_shares,depth_ok=enough,cost=cost))
    print('OPT_LEG',leg.get('market_id'),'LABEL',leg.get('label'),'PRICE',p,'GROSS_NEEDED',gross,'NET_RECEIVED',received,'TOP_SIZE',depth,'DEPTH_OK',enough,'COST',cost)

optimized_collateral=math.prod((float(collateral_multiplier),target))
optimized_profit=optimized_collateral-optimized_cost
optimized_roi=optimized_profit/optimized_cost if optimized_cost>0 else None
print('TARGET_NET_NO_PER_LEG',target)
print('OPTIMIZED_ALL_DEPTH_OK',optimized_depth_ok)
print('OPTIMIZED_TOTAL_PURCHASE_COST',optimized_cost)
print('OPTIMIZED_COLLATERAL_OUT',optimized_collateral)
print('OPTIMIZED_IMMEDIATE_PROFIT',optimized_profit)
print('OPTIMIZED_ROI',optimized_roi)
print('OPTIMIZED_PROFIT_POSITIVE',optimized_profit>0 and optimized_depth_ok)
print('CONVERSION_FEE_BIPS',conversion_fee_bips)
print('COLLATERAL_MULTIPLIER',collateral_multiplier)

stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
outdir=root/'knowledge/raw/market_data/polymarket_negrisk_conversion'
outdir.mkdir(parents=True,exist_ok=True)
out=outdir/(stamp+'-anthropic-548858-e435.json')
payload=dict(retrieved_at=datetime.now(timezone.utc).isoformat(),event_id='548858',books_sha256=books_sha,books_path=str(books_path),conversion_fee_bips=conversion_fee_bips,question_count=question_count,collateral_multiplier=collateral_multiplier,fixed_gross_test=dict(gross_per_leg=fixed_gross,all_depth_ok=fixed_depth_ok,total_purchase_cost=fixed_cost,min_net_no_shares=fixed_convertible,collateral_out=fixed_collateral,conservative_immediate_profit=fixed_profit,roi=fixed_roi),optimized_target_test=dict(target_net_no_per_leg=target,all_depth_ok=optimized_depth_ok,total_purchase_cost=optimized_cost,collateral_out=optimized_collateral,immediate_profit=optimized_profit,roi=optimized_roi,legs=optimized_rows),legs=legs,live_trading=False,paid_actions=False,wallet_actions=False)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')
print('OUTPUT_PATH',out)
print('ANTHROPIC_ALL_NO_CONVERSION_E435_PASS')
