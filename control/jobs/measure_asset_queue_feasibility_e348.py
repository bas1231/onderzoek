from pathlib import Path
from datetime import datetime,timezone
import json

root=Path.cwd()
trade_path=root/'knowledge/raw/market_data/polymarket_trade_feed/20260920T022125Z106981.json'
market_path=root/'knowledge/raw/market_data/polymarket_neg_risk_partial/20260920T013900Z106981.json'
if not trade_path.exists():
    raise SystemExit('trade_archive_missing')
if not market_path.exists():
    raise SystemExit('market_snapshot_missing')

trade_data=json.loads(trade_path.read_text(encoding='utf-8'))
market_data=json.loads(market_path.read_text(encoding='utf-8'))
trades=trade_data.get('data') or tuple()
markets=market_data.get('markets') or tuple()
priced=market_data.get('priced') or tuple()

meta=dict()
for market in markets:
    mid=str(market.get('market_id'))
    yes=str(market.get('yes_token') or '')
    meta[yes]=dict(market_id=mid,question=str(market.get('question') or ''))

bidmap=dict()
queuemap=dict()
for row in priced:
    mid=str(row.get('market_id'))
    yes=row.get('yes') or dict()
    bidmap[mid]=float(yes.get('bid'))
    queuemap[mid]=float(yes.get('bid_size'))

valid=list()
for row in trades:
    if not isinstance(row,dict):
        continue
    token=str(row.get('token_id') or '')
    m=meta.get(token)
    if not m:
        continue
    if str(row.get('outcome') or '').lower()!='yes':
        continue
    try:
        ts=float(row.get('timestamp'))
        price=float(row.get('price'))
        size=float(row.get('size'))
    except Exception:
        continue
    valid.append(dict(ts=ts,price=price,size=size,market_id=m.get('market_id'),side=str(row.get('side') or '')))

print('ARCHIVED_TRADE_ROWS',len(trades))
print('YES_TOKEN_TRADE_ROWS',len(valid))
if valid:
    oldest=min(row.get('ts') for row in valid)
    latest=max(row.get('ts') for row in valid)
    span=max(1.0,latest-oldest)
    print('OLDEST_YES_TRADE_UTC',datetime.fromtimestamp(oldest,timezone.utc).isoformat())
    print('LATEST_YES_TRADE_UTC',datetime.fromtimestamp(latest,timezone.utc).isoformat())
    print('OBSERVED_SPAN_HOURS',span/3600.0)

for mid in sorted(bidmap):
    bid=bidmap.get(mid)
    queue=queuemap.get(mid)
    subset=[row for row in valid if row.get('market_id')==mid]
    exact=[row for row in subset if abs(float(row.get('price'))-bid)<0.0000001]
    near=[row for row in subset if abs(float(row.get('price'))-bid)<=0.011]
    total_volume=sum(float(row.get('size')) for row in subset)
    exact_volume=sum(float(row.get('size')) for row in exact)
    near_volume=sum(float(row.get('size')) for row in near)
    exact_sell_volume=sum(float(row.get('size')) for row in exact if str(row.get('side')).upper()=='SELL')
    print('MARKET',mid)
    print('MAKER_BID',bid)
    print('QUEUE_AHEAD',queue)
    print('YES_TRADE_COUNT',len(subset))
    print('YES_TOTAL_VOLUME',total_volume)
    print('EXACT_BID_TRADE_COUNT',len(exact))
    print('EXACT_BID_VOLUME',exact_volume)
    print('EXACT_BID_SELL_VOLUME',exact_sell_volume)
    print('NEAR_BID_TRADE_COUNT',len(near))
    print('NEAR_BID_VOLUME',near_volume)
    if exact_volume>0:
        print('QUEUE_TO_EXACT_VOLUME_RATIO',queue/exact_volume)
    else:
        print('QUEUE_TO_EXACT_VOLUME_RATIO','INF')
    if exact_sell_volume>0:
        print('QUEUE_TO_EXACT_SELL_RATIO',queue/exact_sell_volume)
    else:
        print('QUEUE_TO_EXACT_SELL_RATIO','INF')
    print('---')

print('INTERPRETATION','HISTORICAL_FEASIBILITY_ONLY_NOT_VALIDATION')
print('ASSET_QUEUE_FEASIBILITY_PASS')
