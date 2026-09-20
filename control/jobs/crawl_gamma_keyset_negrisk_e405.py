from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlencode
from datetime import datetime,timezone
import hashlib
import json
import time

root=Path.cwd()
agent='PredictionEdgeHunter/1.0'
base='https:'+chr(47)+chr(47)+'gamma-api.polymarket.com/events/keyset'
raw_dir=Path.home()/'.local/state/prediction-research/raw/polymarket_gamma_keyset'
raw_dir.mkdir(parents=True,exist_ok=True)

known=set()
for dirname in [root/'knowledge/raw/market_data/polymarket_neg_risk_manifests',root/'knowledge/raw/market_data/polymarket_neg_risk_keyset_manifests']:
    if not dirname.exists():
        continue
    for p in dirname.iterdir():
        if not p.is_file() or p.suffix!='.json':
            continue
        try:
            data=json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            continue
        for key in ['groups','new_groups']:
            for row in data.get(key) or tuple():
                if isinstance(row,dict):
                    eid=str(row.get('event_id') or '')
                    if eid:
                        known.add(eid)

cursor=None
seen_events=set()
seen_cursors=set()
seen_shas=set()
eligible=dict()
pages=list()
raw_bytes_total=0
max_pages=25
previous_ids=set()

for page_index in range(1,max_pages+1):
    params=dict(active='true',closed='false',limit='100')
    if cursor:
        params['after_cursor']=cursor
    url=base+'?'+urlencode(params)
    body=None
    status=None
    error=None
    for attempt in [1,2,3]:
        try:
            req=Request(url,headers={'User-Agent':agent})
            with urlopen(req,timeout=40) as response:
                body=response.read()
                status=response.status
            if status==200:
                break
        except Exception as exc:
            error=str(exc)
            print('PAGE_RETRY',page_index,attempt,error)
            if attempt<3:
                time.sleep(1)
    if body is None or status!=200:
        raise SystemExit('page_fetch_failed_'+str(page_index)+''+str(error))

    sha=hashlib.sha256(body).hexdigest()
    if sha in seen_shas:
        raise SystemExit('page_sha_repeat'+str(page_index))
    seen_shas.add(sha)
    raw_bytes_total+=len(body)
    raw_path=raw_dir/(sha+'.json')
    if not raw_path.exists():
        raw_path.write_bytes(body)

    data=json.loads(body)
    if not isinstance(data,dict):
        raise SystemExit('unexpected_page_shape')
    rows=data.get('events') or tuple()
    if not isinstance(rows,list):
        raise SystemExit('unexpected_events_shape')

    ids=set()
    for event in rows:
        if isinstance(event,dict):
            eid=str(event.get('id') or '')
            if eid:
                ids.add(eid)
    overlap=len(previous_ids.intersection(ids)) if previous_ids else 0
    first_id=str((rows[0] or dict()).get('id') or '') if rows else ''
    last_id=str((rows[-1] or dict()).get('id') or '') if rows else ''
    next_cursor=str(data.get('next_cursor') or '')

    print('PAGE',page_index,'ROWS',len(rows),'FIRST',first_id,'LAST',last_id,'OVERLAP_PREVIOUS',overlap,'SHA',sha)
    if previous_ids and overlap>0:
        raise SystemExit('page_overlap_detected_'+str(page_index))
    if cursor and next_cursor==cursor:
        raise SystemExit('cursor_did_not_advance_'+str(page_index))
    if next_cursor and next_cursor in seen_cursors:
        raise SystemExit('cursor_repeat_'+str(page_index))
    if next_cursor:
        seen_cursors.add(next_cursor)

    pages.append(dict(page=page_index,row_count=len(rows),first_id=first_id,last_id=last_id,overlap_previous=overlap,sha256=sha))
    previous_ids=ids

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
            ids_raw=market.get('clobTokenIds')
            outs=market.get('outcomes')
            if isinstance(ids_raw,str):
                try:
                    ids_raw=json.loads(ids_raw)
                except Exception:
                    ids_raw=None
            if isinstance(outs,str):
                try:
                    outs=json.loads(outs)
                except Exception:
                    outs=None
            if not isinstance(ids_raw,list) or not isinstance(outs,list) or len(ids_raw)!=2 or len(outs)!=2:
                continue
            names=[str(x).lower() for x in outs]
            if 'yes' not in names or 'no' not in names:
                continue
            gid=str(market.get('negRiskMarketID') or '')
            if gid:
                groups.add(gid)
            yi=names.index('yes')
            ni=names.index('no')
            markets.append(dict(market_id=str(market.get('id') or ''),question=str(market.get('question') or ''),yes_token=str(ids_raw[yi]),no_token=str(ids_raw[ni])))
        if len(markets)>=3 and len(markets)<=40 and len(groups)==1:
            eligible[eid]=dict(event_id=eid,title=str(event.get('title') or ''),neg_risk_market_id=next(iter(groups)),market_count=len(markets),markets=markets)

    cursor=next_cursor
    if not cursor:
        print('END_OF_KEYSET',page_index)
        break

new_groups=[row for eid,row in eligible.items() if eid not in known]
new_groups.sort(key=lambda row:int(row.get('event_id')) if str(row.get('event_id')).isdigit() else str(row.get('event_id')))

stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
outdir=root/'knowledge/raw/market_data/polymarket_neg_risk_keyset_manifests'
outdir.mkdir(parents=True,exist_ok=True)
out=outdir/(stamp+'-e405.json')
payload=dict(retrieved_at=datetime.now(timezone.utc).isoformat(),pages_scanned=len(pages),events_seen=len(seen_events),eligible_group_count=len(eligible),known_group_count=len(known),new_group_count=len(new_groups),raw_bytes_total=raw_bytes_total,next_cursor=cursor,live_trading=False,paid_actions=False,wallet_actions=False,pages=pages,new_groups=new_groups)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')

print('PAGES_SCANNED',len(pages))
print('EVENTS_SEEN',len(seen_events))
print('RAW_BYTES_TOTAL',raw_bytes_total)
print('ELIGIBLE_GROUPS',len(eligible))
print('KNOWN_GROUP_COUNT',len(known))
print('NEW_GROUP_COUNT',len(new_groups))
for row in new_groups:
    print('NEW_GROUP',row.get('event_id'),'MARKETS',row.get('market_count'),'TITLE',row.get('title')[:300])
print('NEXT_CURSOR_PRESENT',bool(cursor))
print('PATH',out)
print('GAMMA_KEYSET_NEGRISK_E405_PASS')
