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

sources=[p for p in manifest_dir.iterdir() if p.is_file() and p.name.endswith('-e413.json')]
sources.sort(key=lambda p:p.stat().st_mtime)
if not sources:
    raise SystemExit('e413_manifest_missing')
source_path=sources[-1]
source=json.loads(source_path.read_text(encoding='utf-8'))
cursor=str(source.get('next_cursor') or '')
if not cursor:
    raise SystemExit('continuation_cursor_missing')

prior_events=dict()
for suffix in ['-e405.json','-e413.json']:
    matches=[p for p in manifest_dir.iterdir() if p.is_file() and p.name.endswith(suffix)]
    matches.sort(key=lambda p:p.stat().st_mtime)
    if not matches:
        continue
    manifest=json.loads(matches[-1].read_text(encoding='utf-8'))
    for page in manifest.get('pages') or tuple():
        if not isinstance(page,dict):
            continue
        sha=str(page.get('sha256') or '')
        p=raw_dir/(sha+'.json')
        if not p.exists():
            continue
        data=json.loads(p.read_text(encoding='utf-8'))
        for event in data.get('events') or tuple():
            if isinstance(event,dict):
                eid=str(event.get('id') or '')
                if eid:
                    prior_events[eid]=event

prior_hashes=dict()
for eid,event in prior_events.items():
    if event.get('active') is not True or event.get('closed') is True:
        continue
    if event.get('negRisk') is not True or event.get('negRiskAugmented') is True:
        continue
    desc=str(event.get('description') or '')
    if desc:
        h=hashlib.sha256(desc.encode()).hexdigest()
        prior_hashes.setdefault(h,list()).append(dict(event_id=eid,title=str(event.get('title') or '')))

base='https:'+chr(47)+chr(47)+'gamma-api.polymarket.com/events/keyset'
agent='PredictionEdgeHunter/1.0'
seen_shas=set()
seen_cursors=set([cursor])
previous_ids=set()
pages=list()
new_events=dict()
raw_bytes_total=0

for offset in range(25):
    page_number=51+offset
    params=dict(active='true',closed='false',limit='100',after_cursor=cursor)
    url=base+'?'+urlencode(params)
    body=None
    status=None
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
            if attempt<3:
                time.sleep(1)
    if body is None or status!=200:
        raise SystemExit('page_fetch_failed_'+str(page_number)+''+str(last_error))

    sha=hashlib.sha256(body).hexdigest()
    if sha in seen_shas:
        raise SystemExit('repeated_page_sha'+str(page_number))
    seen_shas.add(sha)
    raw_bytes_total+=len(body)
    raw_path=raw_dir/(sha+'.json')
    if not raw_path.exists():
        raw_path.write_bytes(body)

    data=json.loads(body)
    if not isinstance(data,dict):
        raise SystemExit('bad_page_shape_'+str(page_number))
    rows=data.get('events') or tuple()
    if not isinstance(rows,list):
        raise SystemExit('bad_events_shape_'+str(page_number))

    ids=set()
    for event in rows:
        if isinstance(event,dict):
            eid=str(event.get('id') or '')
            if eid:
                ids.add(eid)
                new_events[eid]=event

    overlap=len(previous_ids.intersection(ids)) if previous_ids else 0
    if previous_ids and overlap>0:
        raise SystemExit('adjacent_page_overlap_'+str(page_number))

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

    previous_ids=ids
    cursor=next_cursor
    if not cursor:
        print('END_OF_KEYSET',page_number)
        break

eligible=list()
for eid,event in new_events.items():
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
    desc_hash=hashlib.sha256(desc.encode()).hexdigest() if desc else ''
    eligible.append(dict(event_id=eid,title=str(event.get('title') or ''),market_count=len(markets),end_date=str(event.get('endDate') or ''),description_sha256=desc_hash,group_id=next(iter(groups))))

eligible.sort(key=lambda row:int(row.get('event_id')) if str(row.get('event_id')).isdigit() else str(row.get('event_id')))

cross_matches=list()
for row in eligible:
    h=str(row.get('description_sha256') or '')
    if h and h in prior_hashes:
        cross_matches.append(dict(new_event=row,prior_events=prior_hashes.get(h)))

stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out=manifest_dir/(stamp+'-e438.json')
payload=dict(retrieved_at=datetime.now(timezone.utc).isoformat(),source_manifest=str(source_path.relative_to(root)),pages_scanned=len(pages),events_seen=len(new_events),eligible_group_count=len(eligible),cross_prior_exact_rule_match_count=len(cross_matches),raw_bytes_total=raw_bytes_total,next_cursor=cursor,pages=pages,eligible_groups=eligible,cross_prior_exact_rule_matches=cross_matches,live_trading=False,paid_actions=False,wallet_actions=False)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')

print('PRIOR_EVENT_COUNT',len(prior_events))
print('PAGES_SCANNED',len(pages))
print('NEW_EVENTS_SEEN',len(new_events))
print('RAW_BYTES_TOTAL',raw_bytes_total)
print('ELIGIBLE_CLEAN_NEGRISK',len(eligible))
print('CROSS_PRIOR_EXACT_RULE_MATCH_COUNT',len(cross_matches))
for match in cross_matches:
    new_row=match.get('new_event') or dict()
    print('RULE_MATCH_NEW',new_row.get('event_id'),'TITLE',str(new_row.get('title') or '')[:400])
    for old in match.get('prior_events') or tuple():
        print('RULE_MATCH_PRIOR',old.get('event_id'),'TITLE',str(old.get('title') or '')[:400])
for row in eligible[:40]:
    print('ELIGIBLE',row.get('event_id'),'MARKETS',row.get('market_count'),'END',row.get('end_date'),'TITLE',str(row.get('title') or '')[:400])
print('NEXT_CURSOR_PRESENT',bool(cursor))
print('OUTPUT_PATH',out)
print('GAMMA_KEYSET_CONTINUATION_E438_PASS')
