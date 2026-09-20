from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import quote
from datetime import datetime,timezone
import json

root=Path.cwd()
base_dir=root/'knowledge/raw/market_data/polymarket_shadow_baselines'
files=list()
if base_dir.exists():
    for p in base_dir.iterdir():
        if p.is_file() and '106981_fill_baseline' in p.name:
            files.append(p)
files.sort(key=lambda p:p.stat().st_mtime)
if not files:
    raise SystemExit('baseline_missing')
baseline_path=files[-1]
baseline=json.loads(baseline_path.read_text(encoding='utf-8'))
credit_raw=str(baseline.get('credit_start') or '')
if not credit_raw:
    raise SystemExit('credit_start_missing')
credit_dt=datetime.fromisoformat(credit_raw)
credit_epoch=int(credit_dt.timestamp())+1
protocol_path=root/'knowledge/candidates/protocols/ASSET-RANK-MAKER-HEDGE-V1-fill-feasibility-24h-v1.json'
protocol=json.loads(protocol_path.read_text(encoding='utf-8'))
window_end_dt=datetime.fromisoformat(str(protocol.get('window_end') or ''))
window_end_epoch=int(window_end_dt.timestamp())-1
now_epoch=int(datetime.now(timezone.utc).timestamp())
upper_credit_epoch=min(now_epoch,window_end_epoch)

meta=dict()
for row in baseline.get('markets') or tuple():
    token=str(row.get('yes_token') or '')
    if not token:
        raise SystemExit('baseline_token_missing')
    mid=str(row.get('market_id') or '')
    bid=float(row.get('best_bid'))
    queue=float(row.get('queue_ahead'))
    meta[token]=dict(market_id=mid,bid=bid,queue=queue)

base_url='https:'+chr(47)+chr(47)+'data-api.polymarket.com/v2/trades?event_id=106981&limit=100&taker_only=true'
cursor=None
pages=list()
rows=list()
seen_cursors=set()
for page_index in range(20):
    url=base_url
    if cursor:
        url=url+'&cursor='+quote(cursor,safe='')
    req=Request(url,headers={'User-Agent':'PredictionEdgeHunter/1.0','Accept':'application/json'})
    with urlopen(req,timeout=30) as r:
        raw=r.read()
        status=r.status
    if status!=200:
        raise SystemExit('trade_http_non_200')
    data=json.loads(raw)
    page_rows=data.get('data') or tuple()
    pagination=data.get('pagination') or dict()
    pages.append(dict(url=url,retrieved_at=datetime.now(timezone.utc).isoformat(),response=data))
    rows.extend(page_rows)
    oldest=None
    for row in page_rows:
        if not isinstance(row,dict):
            continue
        try:
            ts=int(row.get('timestamp'))
        except Exception:
            continue
        if oldest is None or ts<oldest:
            oldest=ts
    if oldest is not None and oldest<credit_epoch:
        break
    next_cursor=pagination.get('next_cursor')
    if not next_cursor:
        break
    cursor=str(next_cursor)
    if cursor in seen_cursors:
        raise SystemExit('cursor_repeat')
    seen_cursors.add(cursor)
else:
    raise SystemExit('pagination_limit_reached')

volume=dict()
trade_count=dict()
for token in meta:
    volume[token]=0.0
    trade_count[token]=0

for row in rows:
    if not isinstance(row,dict):
        continue
    token=str(row.get('token_id') or '')
    info=meta.get(token)
    if not info:
        continue
    try:
        ts=int(row.get('timestamp'))
        price=float(row.get('price'))
        size=float(row.get('size'))
    except Exception:
        continue
    if ts<credit_epoch:
        continue
    if ts>upper_credit_epoch:
        continue
    if str(row.get('side') or '').upper()!='SELL':
        continue
    if abs(price-float(info.get('bid')))>0.0000001:
        continue
    volume[token]=volume.get(token,0.0)+size
    trade_count[token]=trade_count.get(token,0)+1

stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
outdir=root/'knowledge/raw/market_data/polymarket_fill_checkpoints'
outdir.mkdir(parents=True,exist_ok=True)
out=outdir/(stamp+'106981_fill_checkpoint.json')
result=dict(event_id='106981',baseline=str(baseline_path.relative_to(root)),credit_epoch=credit_epoch,credit_start_effective=datetime.fromtimestamp(credit_epoch,timezone.utc).isoformat(),retrieved_at=datetime.now(timezone.utc).isoformat(),pages=pages,markets=list())
result['window_end_effective_epoch']=window_end_epoch
result['upper_credit_epoch']=upper_credit_epoch
result['upper_credit_utc']=datetime.fromtimestamp(upper_credit_epoch,timezone.utc).isoformat()
result['final_window_checkpoint']=now_epoch>window_end_epoch

full_fill_count=0
for token in sorted(meta):
    info=meta.get(token) or dict()
    queue=float(info.get('queue'))
    required=queue+5.0
    consumed=float(volume.get(token,0.0))
    remaining=max(0.0,required-consumed)
    full=consumed>=required
    if full:
        full_fill_count+=1
    item=dict(market_id=info.get('market_id'),yes_token=token,maker_bid=info.get('bid'),initial_queue_ahead=queue,shadow_size=5.0,required_qualifying_volume=required,qualifying_trade_count=trade_count.get(token,0),qualifying_volume=consumed,remaining_to_full_shadow_fill=remaining,full_shadow_fill=full)
    result.get('markets').append(item)
    print('MARKET',item.get('market_id'))
    print('MAKER_BID',item.get('maker_bid'))
    print('INITIAL_QUEUE_AHEAD',item.get('initial_queue_ahead'))
    print('REQUIRED_VOLUME',item.get('required_qualifying_volume'))
    print('QUALIFYING_TRADE_COUNT',item.get('qualifying_trade_count'))
    print('QUALIFYING_VOLUME',item.get('qualifying_volume'))
    print('REMAINING_TO_FILL',item.get('remaining_to_full_shadow_fill'))
    print('FULL_SHADOW_FILL',item.get('full_shadow_fill'))
    print('---')

result['full_shadow_fill_count']=full_fill_count
out.write_text(json.dumps(result,indent=2,sort_keys=True)+chr(10),encoding='utf-8')
print('BASELINE',baseline_path.name)
print('EFFECTIVE_CREDIT_START',result.get('credit_start_effective'))
print('FETCHED_PAGES',len(pages))
print('FETCHED_ROWS',len(rows))
print('FULL_SHADOW_FILL_COUNT',full_fill_count)
print('PATH',out)
print('ASSET_FILL_CHECKPOINT_PASS')
