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
    raise SystemExit('event_http_failed')
event=json.loads(event_raw)

state=Path.home()/'.local/state/prediction-research/raw/polymarket_gamma_events'
state.mkdir(parents=True,exist_ok=True)
event_sha=hashlib.sha256(event_raw).hexdigest()
event_path=state/(event_sha+'.json')
if not event_path.exists():
    event_path.write_bytes(event_raw)

print('EVENT_HTTP_STATUS',event_status)
print('EVENT_SHA256',event_sha)
print('EVENT_RAW_PATH',event_path)
print('EVENT_ID',event.get('id'))
print('TITLE',event.get('title'))
print('NEG_RISK',event.get('negRisk'))
print('NEG_RISK_AUGMENTED',event.get('negRiskAugmented'))
print('EVENT_GROUP_ID',event.get('negRiskMarketID'))
print('EVENT_END_DATE',event.get('endDate'))
print('DESCRIPTION',repr(str(event.get('description') or ''))[:12000])

if event.get('negRisk') is not True:
    raise SystemExit('event_not_negrisk')
if event.get('negRiskAugmented') is True:
    raise SystemExit('event_augmented')

markets=[m for m in event.get('markets') or tuple() if isinstance(m,dict) and m.get('negRisk') is True]
print('MARKET_COUNT',len(markets))
if len(markets)!=10:
    raise SystemExit('unexpected_market_count')

groups=set()
market_ids=set()
request_rows=list()
meta=dict()
description=str(event.get('description') or '')
desc_hash=hashlib.sha256(description.encode()).hexdigest()
all_descriptions_equal=True
all_no_other=True

for market in markets:
    mid=str(market.get('id') or '')
    market_ids.add(mid)
    gid=str(market.get('negRiskMarketID') or '')
    if gid:
        groups.add(gid)
    if market.get('negRiskOther') is True:
        all_no_other=False
    mdesc=str(market.get('description') or '')
    if mdesc!=description:
        all_descriptions_equal=False
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
    fee=market.get('feeSchedule') or dict()
    meta[mid]=dict(question=str(market.get('question') or ''),group_item=str(market.get('groupItemTitle') or ''),end_date=str(market.get('endDate') or ''),group_id=gid,neg_risk_other=market.get('negRiskOther'),fees_enabled=market.get('feesEnabled'),fee_rate=fee.get('rate'),fee_exponent=fee.get('exponent'),taker_only=fee.get('takerOnly'),yes_token=yes_token)
    request_rows.append(dict(token_id=yes_token))

print('GROUP_ID_COUNT',len(groups))
print('GROUP_IDS',sorted(groups))
print('ALL_NO_NEG_RISK_OTHER',all_no_other)
print('ALL_MARKET_DESCRIPTIONS_EQUAL_EVENT',all_descriptions_equal)
print('DESCRIPTION_SHA256',desc_hash)
if len(groups)!=1:
    raise SystemExit('group_id_mismatch')
if not all_no_other:
    raise SystemExit('neg_risk_other_present')
if not all_descriptions_equal:
    raise SystemExit('description_mismatch')

expected_labels=['<$1.25T','$1.25–$1.5T','$1.5–$1.75T','$1.75–$2.0T','$2.0–$2.25T','$2.25–$2.5T','$2.5–$2.75T','$2.75–$3.0T','$3.0T+','No IPO by December 31, 2027']
actual_labels=[str(m.get('groupItemTitle') or '') for m in markets]
print('EXPECTED_LABEL_COUNT',len(expected_labels))
print('ACTUAL_LABELS',actual_labels)
print('LABEL_SET_MATCH',set(actual_labels)==set(expected_labels))
if set(actual_labels)!=set(expected_labels):
    raise SystemExit('bucket_set_mismatch')

books_url='https:'+chr(47)+chr(47)+'clob.polymarket.com/books'
body=json.dumps(request_rows).encode()
req=Request(books_url,data=body,headers={'User-Agent':agent,'Content-Type':'application/json'},method='POST')
with urlopen(req,timeout=40) as response:
    books_raw=response.read()
    books_status=response.status
if books_status!=200:
    raise SystemExit('books_http_failed')
books=json.loads(books_raw)
if not isinstance(books,list):
    raise SystemExit('books_shape_bad')

book_state=Path.home()/'.local/state/prediction-research/raw/polymarket_clob_books'
book_state.mkdir(parents=True,exist_ok=True)
books_sha=hashlib.sha256(books_raw).hexdigest()
books_path=book_state/(books_sha+'.json')
if not books_path.exists():
    books_path.write_bytes(books_raw)
print('BOOKS_HTTP_STATUS',books_status)
print('BOOKS_SHA256',books_sha)
print('BOOKS_RAW_PATH',books_path)
print('BOOK_COUNT',len(books))

bookmap=dict((str(book.get('asset_id')),book) for book in books if isinstance(book,dict))
priced=list()
for mid in sorted(meta.keys(),key=lambda value:int(value)):
    info=meta[mid]
    token=info.get('yes_token')
    book=bookmap.get(str(token))
    if not isinstance(book,dict):
        raise SystemExit('missing_book_'+mid)
    asks=book.get('asks') or tuple()
    bids=book.get('bids') or tuple()
    if not asks:
        raise SystemExit('missing_ask_'+mid)
    ask=min(asks,key=lambda row:float(row.get('price',9)))
    price=float(ask.get('price'))
    size=float(ask.get('size',0))
    if size<=0:
        raise SystemExit('bad_ask_size_'+mid)
    bid_price=None
    bid_size=None
    if bids:
        bid=max(bids,key=lambda row:float(row.get('price',0)))
        bid_price=float(bid.get('price'))
        bid_size=float(bid.get('size',0))
    item=dict(info)
    item['market_id']=mid
    item['ask']=price
    item['ask_size']=size
    item['bid']=bid_price
    item['bid_size']=bid_size
    priced.append(item)

common_size=min(float(item.get('ask_size')) for item in priced)
ask_sum=sum(float(item.get('ask')) for item in priced)
gross_per=1.0-ask_sum
gross_total=math.prod((gross_per,common_size))
fee_known=True
fee_total=0.0

for item in priced:
    enabled=item.get('fees_enabled')
    fee_value=None
    if enabled is False:
        fee_value=0.0
    elif enabled is True:
        try:
            rate=float(item.get('fee_rate'))
            exponent=float(item.get('fee_exponent'))
        except Exception:
            rate=None
            exponent=None
        if rate is not None and exponent==1.0 and item.get('taker_only') is True:
            p=float(item.get('ask'))
            fee_value=round(math.prod((common_size,rate,p,1.0-p)),5)
    if fee_value is None:
        fee_known=False
    else:
        fee_total+=fee_value
    item['fee_at_common_size']=fee_value
    print('LEG',item.get('market_id'),'LABEL',item.get('group_item'),'ASK',item.get('ask'),'ASK_SIZE',item.get('ask_size'),'BID',item.get('bid'),'BID_SIZE',item.get('bid_size'),'FEE',fee_value,'SCHEDULE',item.get('fees_enabled'),item.get('fee_rate'),item.get('fee_exponent'),item.get('taker_only'))

net_total=None
capital=None
net_roi=None
if fee_known:
    net_total=gross_total-fee_total
    capital=math.prod((ask_sum,common_size))+fee_total
    if capital>0:
        net_roi=net_total/capital

print('ASK_SUM',ask_sum)
print('COMMON_SIZE',common_size)
print('GROSS_PER_SET',gross_per)
print('GROSS_TOTAL',gross_total)
print('FEE_KNOWN',fee_known)
print('TAKER_FEES_TOTAL',fee_total if fee_known else None)
print('NET_TOTAL',net_total)
print('NET_ROI',net_roi)
print('NET_POSITIVE',net_total is not None and net_total>0)

screen_dir=root/'knowledge/raw/market_data/polymarket_negrisk_feeaware_screen'
screens=[p for p in screen_dir.iterdir() if p.is_file() and p.name.endswith('-e419.json')]
screens.sort(key=lambda p:p.stat().st_mtime)
prior=None
if screens:
    data=json.loads(screens[-1].read_text(encoding='utf-8'))
    for row in data.get('results') or tuple():
        if isinstance(row,dict) and str(row.get('event_id') or '')=='548858':
            prior=row
            break
print('PRIOR_E419_FOUND',prior is not None)
if prior is not None:
    print('PRIOR_ASK_SUM',prior.get('ask_sum'))
    print('PRIOR_COMMON_SIZE',prior.get('common_size'))
    print('PRIOR_NET_TOTAL',prior.get('net_total'))
    print('PRIOR_NET_ROI',prior.get('net_roi'))

stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
outdir=root/'knowledge/raw/market_data/polymarket_reproductions'
outdir.mkdir(parents=True,exist_ok=True)
out=outdir/(stamp+'-anthropic-548858-e420.json')
payload=dict(retrieved_at=datetime.now(timezone.utc).isoformat(),event_id='548858',event_sha256=event_sha,books_sha256=books_sha,description_sha256=desc_hash,group_ids=sorted(groups),all_no_neg_risk_other=all_no_other,all_market_descriptions_equal_event=all_descriptions_equal,label_set_match=(set(actual_labels)==set(expected_labels)),ask_sum=ask_sum,common_size=common_size,gross_per_set=gross_per,gross_total=gross_total,fee_known=fee_known,taker_fees_total=(fee_total if fee_known else None),net_total=net_total,net_roi=net_roi,net_positive=(net_total is not None and net_total>0),prior_e419=prior,legs=priced,live_trading=False,paid_actions=False,wallet_actions=False)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')
print('OUTPUT_PATH',out)
print('ANTHROPIC_COMPLETE_SET_REPRO_E420_PASS')
