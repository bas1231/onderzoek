from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlencode
from datetime import datetime,timezone
import hashlib
import json
import time

root=Path.cwd()
manifest_dir=root/'knowledge/raw/market_data/polymarket_neg_risk_keyset_manifests'
raw_dir=Path.home()/'.local/state/prediction-research/raw/polymarket_gamma_keyset'
raw_dir.mkdir(parents=True,exist_ok=True)

sources=list()
for suffix in ['-e405.json','-e413.json','-e438.json']:
    matches=[p for p in manifest_dir.iterdir() if p.is_file() and p.name.endswith(suffix)]
    matches.sort(key=lambda p:p.stat().st_mtime)
    if not matches:
        raise SystemExit('manifest_missing_'+suffix)
    sources.append(matches[-1])

latest=json.loads(sources[-1].read_text(encoding='utf-8'))
cursor=str(latest.get('next_cursor') or '')
if not cursor:
    raise SystemExit('e438_cursor_missing')

prior_events=dict()
prior_rule_index=dict()
for manifest_path in sources:
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    for page in manifest.get('pages') or tuple():
        if not isinstance(page,dict):
            continue
        sha=str(page.get('sha256') or '')
        path=raw_dir/(sha+'.json')
        if not path.exists():
            raise SystemExit('prior_raw_missing_'+sha)
        data=json.loads(path.read_text(encoding='utf-8'))
        for event in data.get('events') or tuple():
            if not isinstance(event,dict):
                continue
            eid=str(event.get('id') or '')
            if not eid:
                continue
            prior_events[eid]=event
            if event.get('active') is not True or event.get('closed') is True:
                continue
            if event.get('negRisk') is not True or event.get('negRiskAugmented') is True:
                continue
            markets=[m for m in event.get('markets') or tuple() if isinstance(m,dict) and m.get('negRisk') is True]
            if len(markets)<3 or len(markets)>40:
                continue
            groups=set(str(m.get('negRiskMarketID') or '') for m in markets if str(m.get('negRiskMarketID') or ''))
            if len(groups)!=1:
                continue
            desc=str(event.get('description') or '')
            if not desc:
                continue
            h=hashlib.sha256(desc.encode()).hexdigest()
            prior_rule_index.setdefault(h,list()).append(dict(event_id=eid,title=str(event.get('title') or ''),end_date=str(event.get('endDate') or ''),market_count=len(markets)))

base='https:'+chr(47)+chr(47)+'gamma-api.polymarket.com/events/keyset'
agent='PredictionEdgeHunter/1.0'
seen_cursors=set([cursor])
seen_shas=set()
previous_ids=set()
pages=list()
new_events=dict()
eligible=list()
rule_matches=list()
raw_bytes=0

for offset in range(25):
    page_number=76+offset
    query=urlencode(dict(active='true',closed='false',limit='100',after_cursor=cursor))
    url=base+'?'+query
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
            if attempt<3:
                time.sleep(1)
    if body is None or status!=200:
        raise SystemExit('page_fetch_failed_'+str(page_number)+''+str(error))

    sha=hashlib.sha256(body).hexdigest()
    if sha in seen_shas:
        raise SystemExit('page_sha_repeat'+str(page_number))
    seen_shas.add(sha)
    raw_bytes+=len(body)
    path=raw_dir/(sha+'.json')
    if not path.exists():
        path.write_bytes(body)

    data=json.loads(body)
    if not isinstance(data,dict):
        raise SystemExit('page_shape_bad')
    rows=data.get('events') or tuple()
    if not isinstance(rows,list):
        raise SystemExit('events_shape_bad')

    ids=set()
    for event in rows:
        if isinstance(event,dict):
            eid=str(event.get('id') or '')
            if eid:
                ids.add(eid)
    overlap=len(previous_ids.intersection(ids)) if previous_ids else 0
    if previous_ids and overlap>0:
        raise SystemExit('page_overlap_'+str(page_number))

    next_cursor=str(data.get('next_cursor') or '')
    if next_cursor==cursor:
        raise SystemExit('cursor_did_not_advance_'+str(page_number))
    if next_cursor and next_cursor in seen_cursors:
        raise SystemExit('cursor_repeat_'+str(page_number))
    if next_cursor:
        seen_cursors.add(next_cursor)

    first_id=str((rows[0] or dict()).get('id') or '') if rows else ''
    last_id=str((rows[-1] or dict()).get('id') or '') if rows else ''
    pages.append(dict(page=page_number,row_count=len(rows),first_id=first_id,last_id=last_id,overlap_previous=overlap,sha256=sha))
    print('PAGE',page_number,'ROWS',len(rows),'FIRST',first_id,'LAST',last_id,'OVERLAP',overlap,'SHA',sha)

    for event in rows:
        if not isinstance(event,dict):
            continue
        eid=str(event.get('id') or '')
        if not eid:
            continue
        new_events[eid]=event
        if event.get('active') is not True or event.get('closed') is True:
            continue
        if event.get('negRisk') is not True or event.get('negRiskAugmented') is True:
            continue
        markets=[m for m in event.get('markets') or tuple() if isinstance(m,dict) and m.get('negRisk') is True]
        if len(markets)<3 or len(markets)>40:
            continue
        groups=set(str(m.get('negRiskMarketID') or '') for m in markets if str(m.get('negRiskMarketID') or ''))
        if len(groups)!=1:
            continue
        desc=str(event.get('description') or '')
        h=hashlib.sha256(desc.encode()).hexdigest() if desc else ''
        item=dict(event_id=eid,title=str(event.get('title') or ''),end_date=str(event.get('endDate') or ''),market_count=len(markets),description_sha256=h,neg_risk_market_id=next(iter(groups)))
        eligible.append(item)
        if h and h in prior_rule_index:
            for prior in prior_rule_index.get(h) or tuple():
                rule_matches.append(dict(new=item,prior=prior))

    previous_ids=ids
    cursor=next_cursor
    if not cursor:
        print('END_OF_KEYSET',page_number)
        break

stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out=manifest_dir/(stamp+'-e439.json')
payload=dict(retrieved_at=datetime.now(timezone.utc).isoformat(),source_manifest=str(sources[-1].relative_to(root)),prior_event_count=len(prior_events),pages_scanned=len(pages),new_events_seen=len(new_events),raw_bytes_total=raw_bytes,eligible_clean_negrisk=len(eligible),cross_prior_exact_rule_match_count=len(rule_matches),next_cursor=cursor,pages=pages,eligible=eligible,rule_matches=rule_matches,live_trading=False,paid_actions=False,wallet_actions=False)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')

print('PRIOR_EVENT_COUNT',len(prior_events))
print('PAGES_SCANNED',len(pages))
print('NEW_EVENTS_SEEN',len(new_events))
print('RAW_BYTES_TOTAL',raw_bytes)
print('ELIGIBLE_CLEAN_NEGRISK',len(eligible))
print('CROSS_PRIOR_EXACT_RULE_MATCH_COUNT',len(rule_matches))
for match in rule_matches:
    new=match.get('new') or dict()
    prior=match.get('prior') or dict()
    print('RULE_MATCH_NEW',new.get('event_id'),'END',new.get('end_date'),'TITLE',str(new.get('title') or '')[:500])
    print('RULE_MATCH_PRIOR',prior.get('event_id'),'END',prior.get('end_date'),'TITLE',str(prior.get('title') or '')[:500])
print('NEXT_CURSOR_PRESENT',bool(cursor))
print('OUTPUT_PATH',out)
print('GAMMA_KEYSET_CONTINUATION_E439_PASS')
