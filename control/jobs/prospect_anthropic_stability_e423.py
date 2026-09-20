from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone
import hashlib
import json
import math
import time

root=Path.cwd()
repro_dir=root/'knowledge/raw/market_data/polymarket_reproductions'
files=[p for p in repro_dir.iterdir() if p.is_file() and p.name.endswith('-anthropic-548858-e420.json')]
files.sort(key=lambda p:p.stat().st_mtime)
if not files:
    raise SystemExit('e420_missing')
source_path=files[-1]
source=json.loads(source_path.read_text(encoding='utf-8'))
legs=source.get('legs') or tuple()
if len(legs)!=10:
    raise SystemExit('unexpected_leg_count')
size=5.0
request_rows=[dict(token_id=str(leg.get('yes_token') or '')) for leg in legs]
url='https:'+chr(47)+chr(47)+'clob.polymarket.com/books'
raw_dir=Path.home()/'.local/state/prediction-research/raw/polymarket_clob_books'
raw_dir.mkdir(parents=True,exist_ok=True)

def evaluate(prices,ticks):
    cost=math.prod((size,sum(prices)))
    profits=list()
    for index,leg in enumerate(legs):
        p=float(prices[index])
        rate=float(leg.get('fee_rate'))
        fee_usdc=round(math.prod((size,rate,p,1.0-p)),5)
        fee_shares=fee_usdc/p
        net_shares=size-fee_shares
        profits.append(net_shares-cost)
    base_min=min(profits)
    stressed=list()
    for index in range(len(prices)):
        changed=list(prices)
        changed[index]=min(0.999,float(changed[index])+float(ticks[index]))
        changed_cost=math.prod((size,sum(changed)))
        state_profits=list()
        for state_index,leg in enumerate(legs):
            p=float(changed[state_index])
            rate=float(leg.get('fee_rate'))
            fee_usdc=round(math.prod((size,rate,p,1.0-p)),5)
            fee_shares=fee_usdc/p
            net_shares=size-fee_shares
            state_profits.append(net_shares-changed_cost)
        stressed.append(min(state_profits))
    return dict(ask_sum=sum(prices),purchase_cost=cost,min_guaranteed_profit=base_min,min_guaranteed_roi=(base_min/cost if cost>0 else None),worst_single_leg_one_tick_profit=min(stressed),all_single_leg_one_tick_positive=all(value>0 for value in stressed))

snapshots=list()
count=15
interval=2
for number in range(1,count+1):
    body=json.dumps(request_rows).encode()
    req=Request(url,data=body,headers={'User-Agent':'PredictionEdgeHunter/1.0','Content-Type':'application/json'},method='POST')
    with urlopen(req,timeout=30) as response:
        raw=response.read()
        status=response.status
    if status!=200:
        raise SystemExit('books_http_failed_'+str(number))
    sha=hashlib.sha256(raw).hexdigest()
    raw_path=raw_dir/(sha+'.json')
    if not raw_path.exists():
        raw_path.write_bytes(raw)
    books=json.loads(raw)
    if not isinstance(books,list):
        raise SystemExit('books_shape_bad_'+str(number))
    bookmap=dict((str(book.get('asset_id')),book) for book in books if isinstance(book,dict))
    prices=list()
    depths=list()
    ticks=list()
    for leg in legs:
        token=str(leg.get('yes_token') or '')
        book=bookmap.get(token)
        if not isinstance(book,dict):
            raise SystemExit('book_missing_'+str(leg.get('market_id')))
        asks=book.get('asks') or tuple()
        if not asks:
            raise SystemExit('ask_missing_'+str(leg.get('market_id')))
        top=min(asks,key=lambda row:float(row.get('price',9)))
        prices.append(float(top.get('price')))
        depths.append(float(top.get('size',0)))
        tick_raw=book.get('tick_size')
        if tick_raw is None:
            tick_raw=book.get('minimum_tick_size')
        ticks.append(float(tick_raw) if tick_raw is not None else 0.001)
    metrics=evaluate(prices,ticks)
    top_depth_ok=all(value>=size for value in depths)
    row=dict(snapshot=number,retrieved_at=datetime.now(timezone.utc).isoformat(),sha256=sha,prices=prices,depths=depths,ticks=ticks,top_depth_ok=top_depth_ok,ask_sum=metrics.get('ask_sum'),purchase_cost=metrics.get('purchase_cost'),min_guaranteed_profit=metrics.get('min_guaranteed_profit'),min_guaranteed_roi=metrics.get('min_guaranteed_roi'),worst_single_leg_one_tick_profit=metrics.get('worst_single_leg_one_tick_profit'),all_single_leg_one_tick_positive=metrics.get('all_single_leg_one_tick_positive'))
    snapshots.append(row)
    print('SNAPSHOT',number,'ASK_SUM',row.get('ask_sum'),'DEPTH_OK',top_depth_ok,'MIN_PROFIT',row.get('min_guaranteed_profit'),'MIN_ROI',row.get('min_guaranteed_roi'),'WORST_ONE_TICK',row.get('worst_single_leg_one_tick_profit'),'ONE_TICK_SURVIVES',row.get('all_single_leg_one_tick_positive'),'SHA',sha)
    if number<count:
        time.sleep(interval)

base_positive=[row for row in snapshots if row.get('top_depth_ok') and float(row.get('min_guaranteed_profit'))>0]
stress_positive=[row for row in snapshots if row.get('top_depth_ok') and row.get('all_single_leg_one_tick_positive')]
min_profit=min(float(row.get('min_guaranteed_profit')) for row in snapshots)
max_profit=max(float(row.get('min_guaranteed_profit')) for row in snapshots)
unique_shas=len(set(str(row.get('sha256')) for row in snapshots))

print('SNAPSHOT_COUNT',len(snapshots))
print('UNIQUE_BOOK_SNAPSHOTS',unique_shas)
print('BASE_POSITIVE_WITH_DEPTH_COUNT',len(base_positive))
print('SINGLE_TICK_STRESS_POSITIVE_COUNT',len(stress_positive))
print('MIN_OBSERVED_GUARANTEED_PROFIT',min_profit)
print('MAX_OBSERVED_GUARANTEED_PROFIT',max_profit)

stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out=repro_dir/(stamp+'-anthropic-548858-e423-stability.json')
payload=dict(retrieved_at=datetime.now(timezone.utc).isoformat(),source_e420=str(source_path.relative_to(root)),event_id='548858',snapshot_count=len(snapshots),interval_seconds=interval,gross_shares_per_leg=size,unique_book_snapshots=unique_shas,base_positive_with_depth_count=len(base_positive),single_tick_stress_positive_count=len(stress_positive),min_observed_guaranteed_profit=min_profit,max_observed_guaranteed_profit=max_profit,snapshots=snapshots,live_trading=False,paid_actions=False,wallet_actions=False)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')
print('OUTPUT_PATH',out)
print('ANTHROPIC_STABILITY_E423_PASS')
