from pathlib import Path
import hashlib
import json

root=Path.cwd()
manifest_dir=root/'knowledge/raw/market_data/polymarket_neg_risk_keyset_manifests'
files=[p for p in manifest_dir.iterdir() if p.is_file() and p.name.endswith('-e405.json')]
files.sort(key=lambda p:p.stat().st_mtime)
if not files:
    raise SystemExit('e405_manifest_missing')
manifest=json.loads(files[-1].read_text(encoding='utf-8'))
raw_dir=Path.home()/'.local/state/prediction-research/raw/polymarket_gamma_keyset'

events=dict()
for page in manifest.get('pages') or tuple():
    if not isinstance(page,dict):
        continue
    sha=str(page.get('sha256') or '')
    p=raw_dir/(sha+'.json')
    if not p.exists():
        raise SystemExit('raw_page_missing_'+sha)
    data=json.loads(p.read_text(encoding='utf-8'))
    for event in data.get('events') or tuple():
        if not isinstance(event,dict):
            continue
        eid=str(event.get('id') or '')
        if eid:
            events[eid]=event

eligible=list()
for eid,event in events.items():
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
    desc_hash=hashlib.sha256(desc.encode()).hexdigest()
    eligible.append(dict(event_id=eid,title=str(event.get('title') or ''),description_hash=desc_hash,end_date=str(event.get('endDate') or ''),start_date=str(event.get('startDate') or ''),market_count=len(markets),group_id=next(iter(groups))))

families=dict()
for row in eligible:
    families.setdefault(row.get('description_hash'),list()).append(row)
repeated=[]
for desc_hash,rows in families.items():
    if len(rows)>=2:
        rows.sort(key=lambda row:int(row.get('event_id')) if str(row.get('event_id')).isdigit() else str(row.get('event_id')))
        repeated.append((desc_hash,rows))
repeated.sort(key=lambda item:(-len(item[1]),item[0]))

print('E405_EVENT_COUNT',len(events))
print('ELIGIBLE_CLEAN_NEGRISK',len(eligible))
print('UNIQUE_RULE_HASHES',len(families))
print('REPEATED_RULE_FAMILY_COUNT',len(repeated))
for index,item in enumerate(repeated,1):
    desc_hash=item[0]
    rows=item[1]
    print('FAMILY',index,'SIZE',len(rows),'DESCRIPTION_SHA256',desc_hash)
    for row in rows:
        print('EVENT',row.get('event_id'),'MARKETS',row.get('market_count'),'END',row.get('end_date'),'TITLE',row.get('title')[:500])
    print('---')

nonpolitical_words=['ipo','inflation','gdp','cpi','bond','yield','usd','jpy','home value','gpu','album','auction','earthquake','volcano','tornado','trade deficit','sales','launch']
print('NONPOLITICAL_REPEATED_CANDIDATES')
for desc_hash,rows in repeated:
    text=' '.join(str(row.get('title') or '').lower() for row in rows)
    if any(word in text for word in nonpolitical_words):
        print('CANDIDATE_FAMILY',desc_hash,'SIZE',len(rows))
        for row in rows:
            print('CANDIDATE_EVENT',row.get('event_id'),'MARKETS',row.get('market_count'),'END',row.get('end_date'),'TITLE',row.get('title')[:500])

print('REPEATED_RULE_FAMILY_MINING_E412_PASS')
