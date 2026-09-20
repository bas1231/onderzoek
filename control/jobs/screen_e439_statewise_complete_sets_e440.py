from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone
import hashlib
import json
import math
import time

root=Path.cwd()
manifest_dir=root/'knowledge/raw/market_data/polymarket_neg_risk_keyset_manifests'
raw_gamma=Path.home()/'.local/state/prediction-research/raw/polymarket_gamma_keyset'
raw_books=Path.home()/'.local/state/prediction-research/raw/polymarket_clob_book_batches'
raw_books.mkdir(parents=True,exist_ok=True)

matches=[p for p in manifest_dir.iterdir() if p.is_file() and p.name.endswith('-e439.json')]
matches.sort(key=lambda p:p.stat().st_mtime)
if not matches:
    raise SystemExit('e439_manifest_missing')
manifest_path=matches[-1]
manifest=json.loads(manifest_path.read_text(encoding='utf-8'))

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

events=dict()
for page in manifest.get('pages') or tuple():
    if not isinstance(page,dict):
        continue
    sha=str(page.get('sha256') or '')
    raw_path=raw_gamma/(sha+'.json')
    if not raw_path.exists():
        raise SystemExit('raw_page_missing_'+sha)
    data=json.loads(raw_path.read_text(encoding='utf-8'))
    for event in data.get('events') or tuple():
        if isinstance(event,dict):
            eid=str(event.get('id') or '')
            if eid:
                events[eid]=event

candidates=list()
all_tokens=list()
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
    groups=set(str(m.get('negRiskMarketID') or '') for m in markets if str(m.get('negRiskMarketID') or ''))
    if len(groups)!=1:
        continue
    legs=list()
    valid=True
    for market in markets:
        pair=token_pair(market)
        if pair is None:
            valid=False
            break
        fee=market.get('feeSchedule') or dict()
        leg=dict(market_id=str(market.get('id') or ''),group_item=str(market.get('groupItemTitle') or ''),question=str(market.get('question') or ''),yes_token=pair.get('yes'),fees_enabled=market.get('feesEnabled'),fee_rate=fee.get('rate'),fee_exponent=fee.get('exponent'),taker_only=fee.get('takerOnly'))
        legs.append(leg)
    if valid and len(legs)==len(markets):
        candidate=dict(event_id=eid,title=str(event.get('title') or ''),description=str(event.get('description') or ''),end_date=str(event.get('endDate') or ''),market_count=len(markets),group_id=next(iter(groups)),legs=legs)
        candidates.append(candidate)
        for leg in legs:
            all_tokens.append(str(leg.get('yes_token')))

unique_tokens=list(dict.fromkeys(all_tokens))
print('E439_EVENTS',len(events))
print('SCREEN_CANDIDATE_GROUPS',len(candidates))
print('UNIQUE_YES_TOKENS',len(unique_tokens))

url='https:'+chr(47)+chr(47)+'clob.polymarket.com/books'
bookmap=dict()
batch_size=200
batch_count=0
fetch_failures=0

for start in range(0,len(unique_tokens),batch_size):
    token_batch=unique_tokens[start:start+batch_size]
    request_rows=[dict(token_id=token) for token in token_batch]
    body=json.dumps(request_rows).encode()
    raw=None
    status=None
    for attempt in [1,2,3]:
        try:
            req=Request(url,data=body,headers={'User-Agent':'PredictionEdgeHunter/1.0','Content-Type':'application/json'},method='POST')
            with urlopen(req,timeout=45) as response:
                raw=response.read()
                status=response.status
            if status==200:
                break
        except Exception as exc:
            if attempt==3:
                print('BATCH_FETCH_FAILED',start,str(exc)[:300])
            else:
                time.sleep(1)
    if raw is None or status!=200:
        fetch_failures+=1
        continue
    batch_count+=1
    sha=hashlib.sha256(raw).hexdigest()
    raw_path=raw_books/(sha+'.json')
    if not raw_path.exists():
        raw_path.write_bytes(raw)
    books=json.loads(raw)
    if not isinstance(books,list):
        fetch_failures+=1
        continue
    for book in books:
        if isinstance(book,dict):
            asset=str(book.get('asset_id') or '')
            if asset:
                bookmap[asset]=book
    print('BATCH',batch_count,'TOKENS',len(token_batch),'BOOKS',len(books),'SHA',sha)

results=list()
missing_books=0
unknown_fees=0
for candidate in candidates:
    priced=list()
    valid=True
    for leg in candidate.get('legs') or tuple():
        token=str(leg.get('yes_token') or '')
        book=bookmap.get(token)
        if not isinstance(book,dict):
            valid=False
            break
        asks=book.get('asks') or tuple()
        if not asks:
            valid=False
            break
        top=min(asks,key=lambda row:float(row.get('price',9)))
        price=float(top.get('price'))
        size=float(top.get('size',0))
        if size<=0 or price<=0:
            valid=False
            break
        item=dict(leg)
        item['ask']=price
        item['ask_size']=size
        priced.append(item)
    if not valid or len(priced)!=candidate.get('market_count'):
        missing_books+=1
        continue

    common_size=min(float(item.get('ask_size')) for item in priced)
    ask_sum=sum(float(item.get('ask')) for item in priced)
    purchase_cost=math.prod((common_size,ask_sum))
    states=list()
    fee_known=True
    for item in priced:
        enabled=item.get('fees_enabled')
        fee_shares=None
        fee_usdc=None
        if enabled is False:
            fee_usdc=0.0
            fee_shares=0.0
        elif enabled is True:
            try:
                rate=float(item.get('fee_rate'))
                exponent=float(item.get('fee_exponent'))
            except Exception:
                rate=None
                exponent=None
            if rate is not None and exponent==1.0 and item.get('taker_only') is True:
                p=float(item.get('ask'))
                fee_usdc=round(math.prod((common_size,rate,p,1.0-p)),5)
                fee_shares=fee_usdc/p
        if fee_shares is None:
            fee_known=False
            break
        payout=common_size-fee_shares
        profit=payout-purchase_cost
        states.append(dict(market_id=item.get('market_id'),group_item=item.get('group_item'),ask=item.get('ask'),ask_size=item.get('ask_size'),fee_usdc_equivalent=fee_usdc,fee_shares=fee_shares,state_payout=payout,state_profit=profit))
    if not fee_known:
        unknown_fees+=1
        continue

    profits=[float(state.get('state_profit')) for state in states]
    min_profit=min(profits)
    max_profit=max(profits)
    min_roi=min_profit/purchase_cost if purchase_cost>0 else None
    result=dict(event_id=candidate.get('event_id'),title=candidate.get('title'),description=candidate.get('description'),end_date=candidate.get('end_date'),market_count=candidate.get('market_count'),group_id=candidate.get('group_id'),ask_sum=ask_sum,common_size=common_size,purchase_cost=purchase_cost,min_state_profit=min_profit,max_state_profit=max_profit,min_state_roi=min_roi,all_states_positive=all(value>0 for value in profits),states=states)
    results.append(result)

results.sort(key=lambda row:float(row.get('min_state_profit')),reverse=True)
positive=[row for row in results if row.get('all_states_positive')]

stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
outdir=root/'knowledge/raw/market_data/polymarket_negrisk_statewise_screen'
outdir.mkdir(parents=True,exist_ok=True)
out=outdir/(stamp+'-e440.json')
payload=dict(retrieved_at=datetime.now(timezone.utc).isoformat(),source_manifest=str(manifest_path.relative_to(root)),event_count=len(events),candidate_groups=len(candidates),unique_yes_tokens=len(unique_tokens),book_batches=batch_count,fetch_failures=fetch_failures,priced_groups=len(results),missing_book_groups=missing_books,unknown_fee_groups=unknown_fees,statewise_positive_count=len(positive),results=results,live_trading=False,paid_actions=False,wallet_actions=False)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')

print('BOOK_BATCHES',batch_count)
print('FETCH_FAILURES',fetch_failures)
print('PRICED_GROUPS',len(results))
print('MISSING_BOOK_GROUPS',missing_books)
print('UNKNOWN_FEE_GROUPS',unknown_fees)
print('STATEWISE_POSITIVE_COUNT',len(positive))
for row in results[:40]:
    print('RESULT',row.get('event_id'),'MARKETS',row.get('market_count'),'ASK_SUM',row.get('ask_sum'),'COMMON_SIZE',row.get('common_size'),'MIN_PROFIT',row.get('min_state_profit'),'MAX_PROFIT',row.get('max_state_profit'),'MIN_ROI',row.get('min_state_roi'),'ALL_POSITIVE',row.get('all_states_positive'),'TITLE',str(row.get('title') or '')[:300])
print('OUTPUT_PATH',out)
print('E439_STATEWISE_COMPLETE_SET_SCREEN_E440_PASS')
