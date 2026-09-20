from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone
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
        raw_path=raw_dir/(sha+'.json')
        if not raw_path.exists():
            raise SystemExit('raw_missing_'+sha)
        data=json.loads(raw_path.read_text(encoding='utf-8'))
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
        legs.append(dict(market_id=str(market.get('id') or ''),question=str(market.get('question') or ''),yes_token=pair.get('yes'),fees_enabled=market.get('feesEnabled'),fee_rate=fee.get('rate'),fee_exponent=fee.get('exponent'),taker_only=fee.get('takerOnly')))
    if valid and len(legs)==len(markets):
        candidates.append(dict(event_id=eid,title=str(event.get('title') or ''),market_count=len(markets),group_id=next(iter(groups)),legs=legs))

print('EVENTS_UNIQUE',len(events))
print('CANDIDATE_GROUPS',len(candidates))

url='https:'+chr(47)+chr(47)+'clob.polymarket.com/books'
results=list()
fetch_failures=0
missing_book_groups=0
unknown_fee_groups=0

for index,candidate in enumerate(candidates,1):
    request_rows=[dict(token_id=leg.get('yes_token')) for leg in candidate.get('legs') or tuple()]
    body=json.dumps(request_rows).encode()
    response_body=None
    status=None
    for attempt in [1,2,3]:
        try:
            req=Request(url,data=body,headers={'User-Agent':'PredictionEdgeHunter/1.0','Content-Type':'application/json'},method='POST')
            with urlopen(req,timeout=30) as response:
                response_body=response.read()
                status=response.status
            if status==200:
                break
        except Exception as exc:
            if attempt==3:
                print('FETCH_FAILED',candidate.get('event_id'),str(exc)[:300])
            else:
                time.sleep(1)
    if response_body is None or status!=200:
        fetch_failures+=1
        continue
    books=json.loads(response_body)
    if not isinstance(books,list):
        fetch_failures+=1
        continue
    bookmap=dict((str(book.get('asset_id')),book) for book in books if isinstance(book,dict))

    priced_legs=list()
    valid=True
    for leg in candidate.get('legs') or tuple():
        book=bookmap.get(str(leg.get('yes_token')))
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
        if size<=0:
            valid=False
            break
        item=dict(leg)
        item['ask']=price
        item['ask_size']=size
        priced_legs.append(item)
    if not valid or len(priced_legs)!=candidate.get('market_count'):
        missing_book_groups+=1
        continue

    common_size=min(float(item.get('ask_size')) for item in priced_legs)
    ask_sum=sum(float(item.get('ask')) for item in priced_legs)
    gross_per=1.0-ask_sum
    gross_total=math.prod((gross_per,common_size))

    fee_known=True
    fee_total=0.0
    for item in priced_legs:
        enabled=item.get('fees_enabled')
        if enabled is False:
            value=0.0
        elif enabled is True:
            try:
                rate=float(item.get('fee_rate'))
                exponent=float(item.get('fee_exponent'))
            except Exception:
                rate=None
                exponent=None
            if rate is None or exponent!=1.0 or item.get('taker_only') is not True:
                value=None
            else:
                p=float(item.get('ask'))
                value=round(math.prod((common_size,rate,p,1.0-p)),5)
        else:
            value=None
        if value is None:
            fee_known=False
        else:
            fee_total+=value

    net_total=None
    capital=None
    net_roi=None
    if fee_known:
        net_total=gross_total-fee_total
        capital=math.prod((ask_sum,common_size))+fee_total
        if capital>0:
            net_roi=net_total/capital
    else:
        unknown_fee_groups+=1

    results.append(dict(event_id=candidate.get('event_id'),title=candidate.get('title'),market_count=candidate.get('market_count'),ask_sum=ask_sum,common_size=common_size,gross_per_set=gross_per,gross_total=gross_total,fee_known=fee_known,taker_fees_total=(fee_total if fee_known else None),net_total=net_total,capital=capital,net_roi=net_roi,legs=priced_legs))

results.sort(key=lambda row:float(row.get('net_total')) if row.get('net_total') is not None else -999999,reverse=True)
gross_positive=[row for row in results if float(row.get('gross_per_set'))>0]
net_positive=[row for row in results if row.get('net_total') is not None and float(row.get('net_total'))>0]

stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
outdir=root/'knowledge/raw/market_data/polymarket_negrisk_feeaware_screen'
outdir.mkdir(parents=True,exist_ok=True)
out=outdir/(stamp+'-e419.json')
payload=dict(retrieved_at=datetime.now(timezone.utc).isoformat(),events_universe=len(events),candidate_groups=len(candidates),priced_groups=len(results),fetch_failures=fetch_failures,missing_book_groups=missing_book_groups,unknown_fee_groups=unknown_fee_groups,gross_positive_count=len(gross_positive),net_positive_count=len(net_positive),live_trading=False,paid_actions=False,wallet_actions=False,results=results)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')

print('PRICED_GROUPS',len(results))
print('FETCH_FAILURES',fetch_failures)
print('MISSING_BOOK_GROUPS',missing_book_groups)
print('UNKNOWN_FEE_GROUPS',unknown_fee_groups)
print('GROSS_POSITIVE_COUNT',len(gross_positive))
print('NET_POSITIVE_COUNT',len(net_positive))
for row in results[:40]:
    print('RESULT',row.get('event_id'),'MARKETS',row.get('market_count'),'ASK_SUM',row.get('ask_sum'),'COMMON_SIZE',row.get('common_size'),'GROSS_TOTAL',row.get('gross_total'),'FEES',row.get('taker_fees_total'),'NET_TOTAL',row.get('net_total'),'NET_ROI',row.get('net_roi'),'TITLE',str(row.get('title') or '')[:300])
print('SNAPSHOT_PATH',out)
print('ALL_NEGRISK_FEEAWARE_SCREEN_E419_PASS')
