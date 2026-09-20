from pathlib import Path
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

suffix_map=[
    (' (lower brackets)','lower'),
    (' (middle brackets)','middle'),
    (' (higher brackets)','higher'),
    (' (upper brackets)','higher'),
    (' - lower brackets','lower'),
    (' - middle brackets','middle'),
    (' - higher brackets','higher'),
    (' - upper brackets','higher'),
    (': lower brackets','lower'),
    (': middle brackets','middle'),
    (': higher brackets','higher'),
    (': upper brackets','higher')
]

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
    title=str(event.get('title') or '').strip()
    low=title.lower()
    base_title=title
    tag=''
    for suffix,label in suffix_map:
        if low.endswith(suffix):
            base_title=title[:len(title)-len(suffix)].strip()
            tag=label
            break
    eligible.append(dict(event_id=eid,title=title,base_title=base_title,bracket_tag=tag,market_count=len(markets),end_date=str(event.get('endDate') or ''),description=str(event.get('description') or '')))

families=dict()
for row in eligible:
    key=str(row.get('base_title') or '').lower()
    families.setdefault(key,list()).append(row)

siblings=list()
for key,rows in families.items():
    tags=set(row.get('bracket_tag') for row in rows if row.get('bracket_tag'))
    if len(rows)>=2 and tags:
        rows.sort(key=lambda row:int(row.get('event_id')) if str(row.get('event_id')).isdigit() else str(row.get('event_id')))
        siblings.append((key,rows,tags))
siblings.sort(key=lambda item:(-len(item[1]),item[0]))

print('EVENTS_UNIQUE',len(events))
print('ELIGIBLE_CLEAN_NEGRISK',len(eligible))
print('SIBLING_BRACKET_FAMILY_COUNT',len(siblings))
for index,item in enumerate(siblings,1):
    key=item[0]
    rows=item[1]
    tags=item[2]
    descs=set(row.get('description') for row in rows)
    ends=set(row.get('end_date') for row in rows)
    print('FAMILY',index,'BASE',key,'SIZE',len(rows),'TAGS',sorted(tags))
    print('DESCRIPTION_EQUAL',len(descs)==1)
    print('END_DATE_EQUAL',len(ends)==1)
    for row in rows:
        print('EVENT',row.get('event_id'),'TAG',row.get('bracket_tag'),'MARKETS',row.get('market_count'),'END',row.get('end_date'),'TITLE',row.get('title'))
    print('---')

nonpolitical_terms=['ipo','inflation','gdp','cpi','exchange rate','usd','jpy','bond','yield','home value','gpu','sales','auction','launch','trade deficit','earthquake','volcano','tornado']
print('NONPOLITICAL_SIBLING_CANDIDATES')
for key,rows,tags in siblings:
    text=' '.join(str(row.get('title') or '').lower() for row in rows)
    if any(term in text for term in nonpolitical_terms):
        descs=set(row.get('description') for row in rows)
        ends=set(row.get('end_date') for row in rows)
        print('CANDIDATE_BASE',key,'SIZE',len(rows),'TAGS',sorted(tags))
        print('CANDIDATE_DESCRIPTION_EQUAL',len(descs)==1)
        print('CANDIDATE_END_DATE_EQUAL',len(ends)==1)
        for row in rows:
            print('CANDIDATE_EVENT',row.get('event_id'),'TAG',row.get('bracket_tag'),'MARKETS',row.get('market_count'),'END',row.get('end_date'),'TITLE',row.get('title'))

print('BRACKET_SIBLING_MINING_E415_PASS')
