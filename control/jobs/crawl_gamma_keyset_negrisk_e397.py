from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone
import hashlib
import json
import time

root=Path.cwd()
agent='PredictionEdgeHunter/1.0'
base='https:'+chr(47)+chr(47)+'gamma-api.polymarket.com/events/keyset?active=true&closed=false&limit=100'
state=Path.home()/'.local/state/prediction-research/raw/polymarket_gamma_keyset'
state.mkdir(parents=True,exist_ok=True)

known=set()
manifest_dir=root/'knowledge/raw/market_data/polymarket_neg_risk_manifests'
if manifest_dir.exists():
    for p in manifest_dir.iterdir():
        if not p.is_file() or p.suffix!='.json':
            continue
        try:
            data=json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            continue
        for row in data.get('groups') or tuple():
            if isinstance(row,dict):
                eid=str(row.get('event_id') or '')
                if eid:
                    known.add(eid)

cursor=None
seen_events=set()
eligible=dict()
page_summaries=list()
raw_bytes_total=0
max_pages=25

for page_index in range(1,max_pages+1):
    url=base
    if cursor:
        url=url+'&cursor='+cursor
    body=None
    last_error=None
    for attempt in [1,2,3]:
        try:
            req=Request(url,headers={'User-Agent':agent})
            with urlopen(req,timeout=40) as response:
                body=response.read()
                status=response.status
            if status==200:
                break
        except Exception as exc:
            last_error=str(exc)
            print('PAGE_RETRY',page_index,attempt,last_error)
            if attempt<3:
                time.sleep(1)
    if body is None:
        print('PAGE_FAILED',page_index,last_error)
        break
    raw_bytes_total+=len(body)
    sha=hashlib.sha256(body).hexdigest()
    raw_path=state/(sha+'.json')
    if not raw_path.exists():
        raw_path.write_bytes(body)
    data=json.loads(body)
    if not isinstance(data,dict):
        raise SystemExit('unexpected_keyset_shape')
    rows=data.get('events') or tuple()
    if not isinstance(rows,list):
        raise SystemExit('unexpected_events_shape')
    first_id=None
    last_id=None
    if rows:
        if isinstance(rows[0],dict):
            first_id=str(rows[0].get('id') or '')
        if isinstance(rows[-1],dict):
            last_id=str(rows[-1].get('id') or '')
    page_summaries.append(dict(page=page_index,row_count=len(rows),sha256=sha,first_id=first_id,last_id=last_id))
    print('PAGE',page_index,'ROWS',len(rows),'FIRST',first_id,'LAST',last_id,'SHA',sha)
    for event in rows:
        if not isinstance(event,dict):
            continue
        eid=str(event.get('id') or '')
        if not eid:
            continue
        seen_events.add(eid)
        if event.get('negRisk') is not True:
            continue
        if event.get('negRiskAugmented') is True:
            continue
        markets=list()
        groups=set()
        for market in event.get('markets') or tuple():
            if not isinstance(market,dict):
                continue
            if market.get('negRisk') is not True:
                continue
            ids=market.get('clobTokenIds')
            outs=market.get('outcomes')
            if isinstance(ids,str):
                try:
                    ids=json.loads(ids)
                except Exception:
                    ids=None
            if isinstance(outs,str):
                try:
                    outs=json.loads(outs)
                except Exception:
                    outs=None
            if not isinstance(ids,list) or not isinstance(outs,list) or len(ids)!=2 or len(outs)!=2:
                continue
            names=[str(x).lower() for x in outs]
            if 'yes' not in names or 'no' not in names:
                continue
            gid=str(market.get('negRiskMarketID') or '')
            if gid:
                groups.add(gid)
            yi=names.index('yes')
            ni=names.index('no')
            markets.append(dict(market_id=str(market.get('id') or ''),question=str(market.get('question') or ''),yes_token=str(ids[yi]),no_token=str(ids[ni])))
        if len(markets)>=3 and len(markets)<=40 and len(groups)==1:
            eligible[eid]=dict(event_id=eid,title=str(event.get('title') or ''),neg_risk_market_id=next(iter(groups)),market_count=len(markets),markets=markets)
    cursor=str(data.get('next_cursor') or '')
    if not cursor:
        print('END_OF_KEYSET',page_index)
        break

new_groups=list()
for eid,row in eligible.items():
    if eid not in known:
        new_groups.append(row)
new_groups.sort(key=lambda row:int(row.get('event_id')) if str(row.get('event_id')).isdigit() else str(row.get('event_id')))

stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
outdir=root/'knowledge/raw/market_data/polymarket_neg_risk_keyset_manifests'
outdir.mkdir(parents=True,exist_ok=True)
out=outdir/(stamp+'.json')
payload=dict(retrieved_at=datetime.now(timezone.utc).isoformat(),pages_scanned=len(page_summaries),events_seen=len(seen_events),eligible_group_count=len(eligible),known_group_count=len(known),new_group_count=len(new_groups),raw_bytes_total=raw_bytes_total,next_cursor=cursor,live_trading=False,paid_actions=False,wallet_actions=False,pages=page_summaries,new_groups=new_groups)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')

print('PAGES_SCANNED',len(page_summaries))
print('EVENTS_SEEN',len(seen_events))
print('RAW_BYTES_TOTAL',raw_bytes_total)
print('ELIGIBLE_GROUPS',len(eligible))
print('KNOWN_GROUP_IDS',len(known))
print('NEW_GROUP_COUNT',len(new_groups))
for row in new_groups:
    print('NEW_GROUP',row.get('event_id'),'MARKETS',row.get('market_count'),'TITLE',row.get('title')[:300])
print('NEXT_CURSOR_PRESENT',bool(cursor))
print('PATH',out)
print('GAMMA_KEYSET_NEGRISK_CRAWL_PASS')
