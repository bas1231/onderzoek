from pathlib import Path
import hashlib
import json

root=Path.cwd()
manifest_dir=root/'knowledge/raw/market_data/polymarket_neg_risk_keyset_manifests'
raw_dir=Path.home()/'.local/state/prediction-research/raw/polymarket_gamma_keyset'

manifest_files=list()
for suffix in ['-e405.json','-e413.json']:
    matches=[p for p in manifest_dir.iterdir() if p.is_file() and p.name.endswith(suffix)]
    matches.sort(key=lambda p:p.stat().st_mtime)
    if not matches:
        raise SystemExit('manifest_missing_'+suffix)
    manifest_files.append(matches[-1])

events=dict()
for manifest_path in manifest_files:
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    for page in manifest.get('pages') or tuple():
        if not isinstance(page,dict):
            continue
        sha=str(page.get('sha256') or '')
        raw_path=raw_dir/(sha+'.json')
        if not raw_path.exists():
            raise SystemExit('raw_missing_'+sha)
        data=json.loads(raw_path.read_text(encoding='utf-8'))
        for event in data.get('events') or tuple():
            if isinstance(event,dict):
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
    eligible.append(dict(event_id=eid,title=str(event.get('title') or ''),description_hash=desc_hash,end_date=str(event.get('endDate') or ''),market_count=len(markets),group_id=next(iter(groups))))

families=dict()
for row in eligible:
    families.setdefault(row.get('description_hash'),list()).append(row)

repeated=list()
for desc_hash,rows in families.items():
    if len(rows)>=2:
        rows.sort(key=lambda row:int(row.get('event_id')) if str(row.get('event_id')).isdigit() else str(row.get('event_id')))
        repeated.append((desc_hash,rows))
repeated.sort(key=lambda item:(-len(item[1]),item[0]))

print('EVENTS_UNIQUE',len(events))
print('ELIGIBLE_CLEAN_NEGRISK',len(eligible))
print('UNIQUE_RULE_HASHES',len(families))
print('REPEATED_RULE_FAMILY_COUNT',len(repeated))
for index,item in enumerate(repeated,1):
    desc_hash=item[0]
    rows=item[1]
    titles=set(row.get('title') for row in rows)
    ends=set(row.get('end_date') for row in rows)
    print('FAMILY',index,'SIZE',len(rows),'DESCRIPTION_SHA256',desc_hash)
    print('TITLE_VARIANTS',len(titles))
    print('END_DATE_VARIANTS',len(ends))
    for row in rows:
        print('EVENT',row.get('event_id'),'MARKETS',row.get('market_count'),'END',row.get('end_date'),'TITLE',row.get('title')[:500])
    print('---')

print('NONPOLITICAL_REPEATED_FAMILIES')
terms=['ipo','inflation','gdp','cpi','exchange rate','usd','jpy','bond','yield','home value','gpu','sales','auction','launch','trade deficit','earthquake','volcano','tornado','album','weather','hurricane']
for desc_hash,rows in repeated:
    text=' '.join(str(row.get('title') or '').lower() for row in rows)
    if any(term in text for term in terms):
        print('CANDIDATE_FAMILY',desc_hash,'SIZE',len(rows))
        for row in rows:
            print('CANDIDATE_EVENT',row.get('event_id'),'MARKETS',row.get('market_count'),'END',row.get('end_date'),'TITLE',row.get('title')[:500])

print('EXACT_RULE_FAMILY_MINING_5000_E416_PASS')
