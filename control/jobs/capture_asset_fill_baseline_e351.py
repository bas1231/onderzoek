from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone
import json

root=Path.cwd()
market_path=root/'knowledge/raw/market_data/polymarket_neg_risk_partial/20260920T013900Z106981.json'
protocol_path=root/'knowledge/candidates/protocols/ASSET-RANK-MAKER-HEDGE-V1-fill-feasibility-24h-v1.json'
if not market_path.exists():
    raise SystemExit('market_snapshot_missing')
if not protocol_path.exists():
    raise SystemExit('protocol_missing')

market_data=json.loads(market_path.read_text(encoding='utf-8'))
protocol=json.loads(protocol_path.read_text(encoding='utf-8'))
markets=market_data.get('markets') or tuple()
if len(markets)!=3:
    raise SystemExit('market_count_wrong')

captures=list()
for market in markets:
    token=str(market.get('yes_token') or '')
    mid=str(market.get('market_id') or '')
    question=str(market.get('question') or '')
    if not token:
        raise SystemExit('yes_token_missing')
    url='https:'+chr(47)+chr(47)+'clob.polymarket.com/book?token_id='+token
    requested_at=datetime.now(timezone.utc).isoformat()
    req=Request(url,headers={'User-Agent':'PredictionEdgeHunter/1.0','Accept':'application/json'})
    with urlopen(req,timeout=30) as r:
        raw=r.read()
        status=r.status
    received_at=datetime.now(timezone.utc).isoformat()
    if status!=200:
        raise SystemExit('book_http_non_200')
    book=json.loads(raw)
    bids=book.get('bids') or tuple()
    asks=book.get('asks') or tuple()
    bid_rows=list()
    ask_rows=list()
    for row in bids:
        if not isinstance(row,dict):
            continue
        try:
            bid_rows.append((float(row.get('price')),float(row.get('size'))))
        except Exception:
            continue
    for row in asks:
        if not isinstance(row,dict):
            continue
        try:
            ask_rows.append((float(row.get('price')),float(row.get('size'))))
        except Exception:
            continue
    if not bid_rows or not ask_rows:
        raise SystemExit('incomplete_book')
    best_bid=max(row[0] for row in bid_rows)
    best_ask=min(row[0] for row in ask_rows)
    queue=sum(row[1] for row in bid_rows if abs(row[0]-best_bid)<0.0000001)
    ask_size=sum(row[1] for row in ask_rows if abs(row[0]-best_ask)<0.0000001)
    captures.append(dict(market_id=mid,question=question,yes_token=token,requested_at=requested_at,received_at=received_at,http_status=status,best_bid=best_bid,queue_ahead=queue,best_ask=best_ask,best_ask_size=ask_size,raw_book=book))

captured_at=datetime.now(timezone.utc)
outdir=root/'knowledge/raw/market_data/polymarket_shadow_baselines'
outdir.mkdir(parents=True,exist_ok=True)
stamp=captured_at.strftime('%Y%m%dT%H%M%SZ')
out=outdir/(stamp+'106981_fill_baseline.json')
payload=dict(protocol_id=protocol.get('protocol_id'),protocol_window_start=protocol.get('window_start'),baseline_captured_at=captured_at.isoformat(),credit_start=captured_at.isoformat(),pre_baseline_fill_credit=False,event_id='106981',markets=captures)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')

print('PROTOCOL_ID',protocol.get('protocol_id'))
print('PROTOCOL_WINDOW_START',protocol.get('window_start'))
print('BASELINE_CAPTURED_AT',payload.get('baseline_captured_at'))
print('CREDIT_START',payload.get('credit_start'))
print('PRE_BASELINE_FILL_CREDIT',payload.get('pre_baseline_fill_credit'))
for row in captures:
    print('MARKET',row.get('market_id'))
    print('BEST_BID',row.get('best_bid'))
    print('QUEUE_AHEAD',row.get('queue_ahead'))
    print('BEST_ASK',row.get('best_ask'))
    print('BEST_ASK_SIZE',row.get('best_ask_size'))
    print('---')
print('PATH',out)
print('ASSET_FILL_BASELINE_CAPTURE_PASS')
