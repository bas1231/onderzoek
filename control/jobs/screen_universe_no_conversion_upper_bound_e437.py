from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone
import itertools
import json
import math
import time

root=Path.cwd()
manifest_dir=root/'knowledge/raw/market_data/polymarket_neg_risk_keyset_manifests'
raw_dir=Path.home()/'.local/state/prediction-research/raw/polymarket_gamma_keyset'

manifest_files=list()
for suffix in ['-e405.json','-e413.json']:
    matches=[p for p in manifest_dir.iterdir() if p.is_file() and p.name.endswith(suffix)]
    matches.sort(key=lambda p:p.stat().st_mtime)
    if not matches:
        raise SystemExit('manifest_missing_'+suffix)
    manifest_files.append(matches[-1])

events=dict()
for manifest_path in manifest_files:
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    for page in manifest.get('pages') or tuple():
        if not isinstance(page,dict):
            continue
        sha=str(page.get('sha256') or '')
        p=raw_dir/(sha+'.json')
        if not p.exists():
            raise SystemExit('raw_missing_'+sha)
        data=json.loads(p.read_text(encoding='utf-8'))
        for event in data.get('events') or tuple():
            if isinstance(event,dict):
                eid=str(event.get('id') or '')
                if eid:
                    events[eid]=event

def token_pair(market):
    ids_raw=market.get('clobTokenIds')
    outcomes=market.get('outcomes')
    if isinstance(ids_raw,str):
        try:
            ids_raw=json.loads(ids_raw)
        except Exception:
            return None
    if isinstance(outcomes,str):
        try:
            outcomes=json.loads(outcomes)
        except Exception:
            return None
    if not isinstance(ids_raw,list) or not isinstance(outcomes,list):
        return None
    if len(ids_raw)!=2 or len(outcomes)!=2:
        return None
    names=[str(value).lower() for value in outcomes]
    if 'yes' not in names or 'no' not in names:
        return None
    return dict(yes=str(ids_raw[names.index('yes')]),no=str(ids_raw[names.index('no')]))

candidates=list()
for eid,event in events.items():
    if event.get('active') is not True or event.get('closed') is True:
        continue
    if event.get('negRisk') is not True or event.get('negRiskAugmented') is True:
        continue
    markets=[m for m in event.get('markets') or tuple() if isinstance(m,dict) and m.get('negRisk') is True]
    if len(markets)<3 or len(markets)>12:
        continue
    if any(m.get('negRiskOther') is True for m in markets):
        continue
    gids=set(str(m.get('negRiskMarketID') or '') for m in markets if str(m.get('negRiskMarketID') or ''))
    if len(gids)!=1:
        continue
    legs=list()
    valid=True
    for market in markets:
        pair=token_pair(market)
        if pair is None:
            valid=False
            break
        fee=market.get('feeSchedule') or dict()
        legs.append(dict(market_id=str(market.get('id') or ''),label=str(market.get('groupItemTitle') or ''),yes_token=pair.get('yes'),no_token=pair.get('no'),fees_enabled=market.get('feesEnabled'),fee_rate=fee.get('rate'),fee_exponent=fee.get('exponent'),taker_only=fee.get('takerOnly')))
    if valid:
        candidates.append(dict(event_id=eid,title=str(event.get('title') or ''),market_count=len(legs),group_id=next(iter(gids)),legs=legs))

print('EVENTS_UNIVERSE',len(events))
print('CANDIDATE_GROUPS',len(candidates))

books_url='https:'+chr(47)+chr(47)+'clob.polymarket.com/books'
gross_buy_size=5.0
priced_groups=0
fetch_failures=0
subset_total=0
positive=list()
best_by_group=list()

for group_index,candidate in enumerate(candidates,1):
    request_rows=list()
    for leg in candidate.get('legs') or tuple():
        request_rows.append(dict(token_id=leg.get('yes_token')))
        request_rows.append(dict(token_id=leg.get('no_token')))
    body=json.dumps(request_rows).encode()
    raw=None
    status=None
    for attempt in [1,2,3]:
        try:
            req=Request(books_url,data=body,headers={'User-Agent':'PredictionEdgeHunter/1.0','Content-Type':'application/json'},method='POST')
            with urlopen(req,timeout=30) as response:
                raw=response.read()
                status=response.status
            if status==200:
                break
        except Exception as exc:
            if attempt<3:
                time.sleep(1)
            else:
                print('FETCH_FAILED',candidate.get('event_id'),str(exc)[:200])
    if raw is None or status!=200:
        fetch_failures+=1
        continue
    books=json.loads(raw)
    if not isinstance(books,list):
        fetch_failures+=1
        continue
    bookmap=dict((str(book.get('asset_id')),book) for book in books if isinstance(book,dict))

    legs=list()
    valid=True
    for leg in candidate.get('legs') or tuple():
        yes_book=bookmap.get(str(leg.get('yes_token')))
        no_book=bookmap.get(str(leg.get('no_token')))
        if not isinstance(yes_book,dict) or not isinstance(no_book,dict):
            valid=False
            break
        yes_bids=yes_book.get('bids') or tuple()
        no_asks=no_book.get('asks') or tuple()
        if not yes_bids or not no_asks:
            valid=False
            break
        yes_bid=max(float(row.get('price',0)) for row in yes_bids)
        no_ask=min(float(row.get('price',9)) for row in no_asks)
        row=dict(leg)
        row['yes_bid']=yes_bid
        row['no_ask']=no_ask
        legs.append(row)
    if not valid:
        continue
    priced_groups+=1
    n=len(legs)
    group_best=None

    for m in range(2,n+1):
        for indexes in itertools.combinations(range(n),m):
            subset_total+=1
            chosen=set(indexes)
            received_no=list()
            buy_cost=0.0
            for index in indexes:
                leg=legs[index]
                p=float(leg.get('no_ask'))
                buy_cost+=math.prod((gross_buy_size,p))
                rate=0.0
                if leg.get('fees_enabled') is True:
                    try:
                        if float(leg.get('fee_exponent'))==1.0 and leg.get('taker_only') is True:
                            rate=float(leg.get('fee_rate'))
                    except Exception:
                        rate=0.0
                fee_usdc=round(math.prod((gross_buy_size,rate,p,1.0-p)),5)
                fee_shares=fee_usdc/p if p>0 else 0.0
                received_no.append(gross_buy_size-fee_shares)
            amount=min(received_no)
            collateral=math.prod((float(m-1),amount))
            yes_sales=0.0
            for index in range(n):
                if index in chosen:
                    continue
                leg=legs[index]
                p=float(leg.get('yes_bid'))
                gross_sale=math.prod((amount,p))
                rate=0.0
                if leg.get('fees_enabled') is True:
                    try:
                        if float(leg.get('fee_exponent'))==1.0 and leg.get('taker_only') is True:
                            rate=float(leg.get('fee_rate'))
                    except Exception:
                        rate=0.0
                sell_fee=round(math.prod((amount,rate,p,1.0-p)),5)
                yes_sales+=gross_sale-sell_fee
            profit=collateral+yes_sales-buy_cost
            roi=profit/buy_cost if buy_cost>0 else None
            result=dict(event_id=candidate.get('event_id'),title=candidate.get('title'),subset_size=m,market_count=n,ids=[legs[index].get('market_id') for index in indexes],labels=[legs[index].get('label') for index in indexes],gross_buy_size=gross_buy_size,convertible_amount=amount,buy_cost=buy_cost,collateral_out=collateral,yes_sales_net=yes_sales,profit_upper_bound=profit,roi_upper_bound=roi,conversion_fee_bips_assumed=0,gas_assumed=0,sell_depth_assumed_unlimited=True)
            if group_best is None or float(result.get('profit_upper_bound'))>float(group_best.get('profit_upper_bound')):
                group_best=result
            if profit>0:
                positive.append(result)

    if group_best is not None:
        best_by_group.append(group_best)

best_by_group.sort(key=lambda row:float(row.get('profit_upper_bound')),reverse=True)
positive.sort(key=lambda row:float(row.get('profit_upper_bound')),reverse=True)

stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
outdir=root/'knowledge/raw/market_data/polymarket_negrisk_conversion'
outdir.mkdir(parents=True,exist_ok=True)
out=outdir/(stamp+'-e437-universe-upper-bound.json')
payload=dict(retrieved_at=datetime.now(timezone.utc).isoformat(),events_universe=len(events),candidate_groups=len(candidates),priced_groups=priced_groups,fetch_failures=fetch_failures,subset_total=subset_total,positive_upper_bound_count=len(positive),assumptions=dict(conversion_fee_bips=0,gas=0,sell_depth='unlimited at best bid',gross_no_buy_size=gross_buy_size,unknown_trading_fee='treated as zero'),best_by_group=best_by_group,positive_upper_bound=positive,live_trading=False,paid_actions=False,wallet_actions=False)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')

print('PRICED_GROUPS',priced_groups)
print('FETCH_FAILURES',fetch_failures)
print('SUBSETS_TOTAL',subset_total)
print('POSITIVE_UPPER_BOUND_COUNT',len(positive))
for index,row in enumerate(positive[:40],1):
    print('POSITIVE',index,'EVENT',row.get('event_id'),'SUBSET',row.get('subset_size'),'OF',row.get('market_count'),'PROFIT',row.get('profit_upper_bound'),'ROI',row.get('roi_upper_bound'),'BUY_COST',row.get('buy_cost'),'COLLATERAL',row.get('collateral_out'),'YES_SALES',row.get('yes_sales_net'),'TITLE',str(row.get('title') or '')[:300],'IDS',row.get('ids'))
print('BEST_GROUPS')
for index,row in enumerate(best_by_group[:30],1):
    print('BEST',index,'EVENT',row.get('event_id'),'SUBSET',row.get('subset_size'),'OF',row.get('market_count'),'PROFIT',row.get('profit_upper_bound'),'ROI',row.get('roi_upper_bound'),'TITLE',str(row.get('title') or '')[:300])
print('OUTPUT_PATH',out)
print('UNIVERSE_NO_CONVERSION_UPPER_BOUND_E437_PASS')
