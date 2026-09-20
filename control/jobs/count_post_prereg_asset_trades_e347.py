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
rows=trade_data.get('data') or tuple()
markets=market_data.get('markets') or tuple()

prereg=datetime.fromisoformat('2026-09-20T02:10:18.043370+00:00').timestamp()
shadow_start=datetime.fromisoformat('2026-09-20T02:15:21.591766+00:00').timestamp()

token_meta=dict()
for market in markets:
    mid=str(market.get('market_id'))
    question=str(market.get('question') or '')
    yes=str(market.get('yes_token') or '')
    no=str(market.get('no_token') or '')
    token_meta[yes]=dict(market_id=mid,side='YES',question=question)
    token_meta[no]=dict(market_id=mid,side='NO',question=question)

post_prereg=list()
post_shadow=list()
latest=None
for row in rows:
    if not isinstance(row,dict):
        continue
    try:
        ts=float(row.get('timestamp'))
    except Exception:
        continue
    if latest is None or ts>latest:
        latest=ts
    if ts>=prereg:
        post_prereg.append(row)
    if ts>=shadow_start:
        post_shadow.append(row)

print('ROW_COUNT',len(rows))
print('PREREG_EPOCH',prereg)
print('SHADOW_START_EPOCH',shadow_start)
if latest is not None:
    print('LATEST_TRADE_EPOCH',latest)
    print('LATEST_TRADE_UTC',datetime.fromtimestamp(latest,timezone.utc).isoformat())
    print('SECONDS_BEFORE_PREREG',prereg-latest)
print('POST_PREREG_COUNT',len(post_prereg))
print('POST_SHADOW_START_COUNT',len(post_shadow))

for label,subset in [('POST_PREREG',post_prereg),('POST_SHADOW',post_shadow)]:
    counts=dict()
    for row in subset:
        token=str(row.get('token_id') or '')
        meta=token_meta.get(token) or dict(side='UNKNOWN',market_id='UNKNOWN',question='')
        key=str(meta.get('market_id'))+'_'+str(meta.get('side'))
        counts[key]=counts.get(key,0)+1
    for key in sorted(counts):
        print(label+'TOKEN_COUNT',key,counts.get(key))

for row in post_shadow[:20]:
    token=str(row.get('token_id') or '')
    meta=token_meta.get(token) or dict(side='UNKNOWN',market_id='UNKNOWN',question='')
    print('POST_SHADOW_TRADE',row.get('timestamp'),meta.get('market_id'),meta.get('side'),row.get('side'),row.get('price'),row.get('size'),row.get('transaction_hash'))

if len(post_prereg)==0:
    print('RESULT','NO_POST_PREREG_TRADES_IN_LATEST_100')
elif len(post_shadow)==0:
    print('RESULT','POST_PREREG_TRADES_EXIST_BUT_NONE_AFTER_SHADOW_START')
else:
    print('RESULT','POST_SHADOW_TRADES_AVAILABLE_FOR_FILL_ANALYSIS')
print('ASSET_POST_PREREG_TRADE_COUNT_PASS')
