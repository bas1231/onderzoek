from pathlib import Path
import json

root=Path.cwd()
base=root/'knowledge/raw/market_data/polymarket_neg_risk_manifests'
if not base.exists():
    raise SystemExit('manifest_dir_missing')
files=[p for p in base.iterdir() if p.is_file() and p.suffix=='.json']
files.sort(key=lambda p:p.stat().st_mtime)
if not files:
    raise SystemExit('manifest_missing')
p=files[-1]
data=json.loads(p.read_text(encoding='utf-8'))
groups=data.get('groups') or tuple()
tested={'48292','51456','79137','79905','85579','86426','102763','106981'}
print('MANIFEST',p.name)
print('GROUP_COUNT',len(groups))
untested=0
for row in groups:
    if not isinstance(row,dict):
        continue
    eid=str(row.get('event_id') or '')
    title=str(row.get('title') or '')
    count=row.get('market_count')
    status='TESTED' if eid in tested else 'UNTESTED'
    if status=='UNTESTED':
        untested+=1
    print('GROUP',eid,'MARKETS',count,'STATUS',status,'TITLE',title[:300])
print('KNOWN_TESTED_COUNT',len([row for row in groups if isinstance(row,dict) and str(row.get('event_id') or '') in tested]))
print('UNTESTED_COUNT',untested)
print('EXTENDED_NEG_RISK_INVENTORY_PASS')
