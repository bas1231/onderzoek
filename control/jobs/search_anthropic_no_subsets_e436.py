from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone
from itertools import combinations
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

if event.get('negRisk') is not True or event.get('negRiskAugmented') is True:
    raise SystemExit('event_not_clean_negrisk')
markets=[m for m in event.get('markets') or tuple() if isinstance(m,dict) and m.get('negRisk') is True]
if len(markets)!=10:
    raise SystemExit('unexpected_market_count')
if any(m.get('negRiskOther') is True for m in markets):
    raise SystemExit('neg_risk_other_present')

conversion_dir=root/'knowledge/raw/market_data/polymarket_negrisk_conversion'
fee_files=[p for p in conversion_dir.iterdir() if p.is_file() and p.name.endswith('-anthropic-548858-e435.json')]
fee_files.sort(key=lambda p:p.stat().st_mtime)
if not fee_files:
    raise SystemExit('e435_missing')
e435=json.loads(fee_files[-1].read_text(encoding='utf-8'))
conversion_fee_bips=int(e435.get('conversion_fee_bips',-1))
if conversion_fee_bips!=0:
    raise SystemExit('conversion_fee_not_zero')

legs=list()
request_rows=list()
for market in markets:
    mid=str(market.get('id') or '')
    ids_raw=market.get('clobTokenIds')
    outcomes=market.get('outcomes')
    if isinstance(ids_raw,str):
        ids_raw=json.loads(ids_raw)
    if isinstance(outcomes,str):
        outcomes=json.loads(outcomes)
    if not isinstance(ids_raw,list) or not isinstance(outcomes,list) or len(ids_raw)!=2 or len(outcomes)!=2:
        raise SystemExit('token_shape_bad_'+mid)
    names=[str(value).lower() for value in outcomes]
    if 'yes' not in names or 'no' not in names:
        raise SystemExit('outcome_shape_bad_'+mid)
    yes_token=str(ids_raw[names.index('yes')])
    no_token=str(ids_raw[names.index('no')])
    fee=market.get('feeSchedule') or dict()
    if market.get('feesEnabled') is not True:
        raise SystemExit('fees_not_enabled_'+mid)
    if float(fee.get('exponent'))!=1.0 or fee.get('takerOnly') is not True:
        raise SystemExit('unsupported_fee_schedule_'+mid)
    rate=float(fee.get('rate'))
    legs.append(dict(market_id=mid,label=str(market.get('groupItemTitle') or ''),yes_token=yes_token,no_token=no_token,fee_rate=rate))
    request_rows.append(dict(token_id=yes_token))
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
raw_path=raw_dir/(books_sha+'.json')
if not raw_path.exists():
    raw_path.write_bytes(books_raw)

for leg in legs:
    no_book=bookmap.get(str(leg.get('no_token')))
    yes_book=bookmap.get(str(leg.get('yes_token')))
    if not isinstance(no_book,dict) or not isinstance(yes_book,dict):
        raise SystemExit('book_missing_'+str(leg.get('market_id')))
    no_asks=no_book.get('asks') or tuple()
    yes_bids=yes_book.get('bids') or tuple()
    if not no_asks or not yes_bids:
        raise SystemExit('side_missing_'+str(leg.get('market_id')))
    no_top=min(no_asks,key=lambda row:float(row.get('price',9)))
    yes_top=max(yes_bids,key=lambda row:float(row.get('price',0)))
    no_tick=no_book.get('tick_size')
    if no_tick is None:
        no_tick=no_book.get('minimum_tick_size')
    yes_tick=yes_book.get('tick_size')
    if yes_tick is None:
        yes_tick=yes_book.get('minimum_tick_size')
    leg['no_ask']=float(no_top.get('price'))
    leg['no_ask_size']=float(no_top.get('size',0))
    leg['yes_bid']=float(yes_top.get('price'))
    leg['yes_bid_size']=float(yes_top.get('size',0))
    leg['no_tick']=float(no_tick) if no_tick is not None else 0.001
    leg['yes_tick']=float(yes_tick) if yes_tick is not None else 0.001
    print('LEG',leg.get('market_id'),'LABEL',leg.get('label'),'NO_ASK',leg.get('no_ask'),'NO_DEPTH',leg.get('no_ask_size'),'YES_BID',leg.get('yes_bid'),'YES_DEPTH',leg.get('yes_bid_size'),'FEE_RATE',leg.get('fee_rate'))

buy_gross=5.0
for leg in legs:
    p=float(leg.get('no_ask'))
    rate=float(leg.get('fee_rate'))
    fee_usdc=round(math.prod((buy_gross,rate,p,1.0-p)),5)
    fee_shares=fee_usdc/p
    leg['buy_cost']=math.prod((buy_gross,p))
    leg['buy_fee_usdc_equivalent']=fee_usdc
    leg['buy_fee_shares']=fee_shares
    leg['net_no_shares']=buy_gross-fee_shares

results=list()
indices=list(range(len(legs)))
for subset_size in range(2,len(legs)+1):
    for subset_tuple in combinations(indices,subset_size):
        chosen=set(subset_tuple)
        bought=[legs[i] for i in subset_tuple]
        complement=[legs[i] for i in indices if i not in chosen]
        buy_depth_ok=all(float(leg.get('no_ask_size'))>=buy_gross for leg in bought)
        amount=min(float(leg.get('net_no_shares')) for leg in bought)
        buy_cost=sum(float(leg.get('buy_cost')) for leg in bought)
        multiplier=subset_size-1
        collateral_out=math.prod((amount,float(multiplier)))
        sell_depth_ok=True
        sell_proceeds=0.0
        sells=list()
        for leg in complement:
            bid=float(leg.get('yes_bid'))
            depth=float(leg.get('yes_bid_size'))
            if depth<amount:
                sell_depth_ok=False
            rate=float(leg.get('fee_rate'))
            gross_proceeds=math.prod((amount,bid))
            fee_usdc=round(math.prod((amount,rate,bid,1.0-bid)),5)
            net_proceeds=gross_proceeds-fee_usdc
            sell_proceeds+=net_proceeds
            sells.append(dict(market_id=leg.get('market_id'),label=leg.get('label'),shares=amount,bid=bid,bid_size=depth,gross_proceeds=gross_proceeds,sell_fee_usdc=fee_usdc,net_proceeds=net_proceeds))
        immediate_cash=collateral_out+sell_proceeds
        profit=immediate_cash-buy_cost
        roi=profit/buy_cost if buy_cost>0 else None
        leftovers=sum(float(leg.get('net_no_shares'))-amount for leg in bought)
        executable=buy_depth_ok and sell_depth_ok
        results.append(dict(subset_size=subset_size,bought_market_ids=[leg.get('market_id') for leg in bought],bought_labels=[leg.get('label') for leg in bought],conversion_amount=amount,buy_cost=buy_cost,collateral_multiplier=multiplier,collateral_out=collateral_out,sell_proceeds=sell_proceeds,immediate_cash=immediate_cash,conservative_profit=profit,conservative_roi=roi,buy_depth_ok=buy_depth_ok,sell_depth_ok=sell_depth_ok,executable_top_level=executable,leftover_no_shares_ignored=leftovers,sells=sells))

executable=[row for row in results if row.get('executable_top_level')]
executable.sort(key=lambda row:float(row.get('conservative_profit')),reverse=True)
positive=[row for row in executable if float(row.get('conservative_profit'))>0]

print('BOOKS_SHA256',books_sha)
print('CONVERSION_FEE_BIPS',conversion_fee_bips)
print('SUBSETS_TOTAL',len(results))
print('EXECUTABLE_TOP_LEVEL_COUNT',len(executable))
print('POSITIVE_IMMEDIATE_COUNT',len(positive))
for rank,row in enumerate(executable[:30],1):
    print('RESULT',rank,'SIZE',row.get('subset_size'),'PROFIT',row.get('conservative_profit'),'ROI',row.get('conservative_roi'),'BUY_COST',row.get('buy_cost'),'COLLATERAL',row.get('collateral_out'),'YES_SALES',row.get('sell_proceeds'),'AMOUNT',row.get('conversion_amount'),'LEFTOVER_NO_IGNORED',row.get('leftover_no_shares_ignored'),'IDS',row.get('bought_market_ids'),'LABELS',row.get('bought_labels'))

stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out=conversion_dir/(stamp+'-anthropic-548858-e436-subsets.json')
payload=dict(retrieved_at=datetime.now(timezone.utc).isoformat(),event_id='548858',books_sha256=books_sha,conversion_fee_bips=conversion_fee_bips,buy_gross_shares_per_selected_no=buy_gross,subset_count=len(results),executable_top_level_count=len(executable),positive_immediate_count=len(positive),fee_model='BUY fee deducted in shares; SELL fee deducted from USDC proceeds; conversion fee from E435',leftover_no_value='ignored conservatively',results=results,live_trading=False,paid_actions=False,wallet_actions=False)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')
print('OUTPUT_PATH',out)
print('ANTHROPIC_NO_SUBSET_SEARCH_E436_PASS')
