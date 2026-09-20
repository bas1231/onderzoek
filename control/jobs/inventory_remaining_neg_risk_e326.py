from pathlib import Path
import json

root=Path.cwd()
base=root/'knowledge/raw/market_data/polymarket_neg_risk_manifests'
files=list()
if base.exists():
    for p in base.iterdir():
        if p.is_file() and p.suffix=='.json':
            files.append(p)
files.sort(key=lambda p:p.stat().st_mtime)
if not files:
    raise SystemExit('manifest_missing')
manifest=json.loads(files[-1].read_text(encoding='utf-8'))
completed={'48292','79137','51456','79905','86426','102763','85579'}
groups=manifest.get('groups') or tuple()
print('MANIFEST',files[-1].name)
print('GROUP_COUNT',len(groups))
remaining=0
for row in groups:
    eid=str(row.get('event_id'))
    title=str(row.get('title') or '')
    count=row.get('market_count')
    status='TESTED' if eid in completed else 'UNTESTED'
    if status=='UNTESTED':
        remaining+=1
    print('GROUP',eid,'MARKETS',count,'STATUS',status,'TITLE',title)
print('TESTED_COUNT',len(completed))
print('UNTESTED_COUNT',remaining)
print('NEG_RISK_REMAINING_INVENTORY_PASS')
