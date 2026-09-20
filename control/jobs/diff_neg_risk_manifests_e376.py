from pathlib import Path
import json

root=Path.cwd()
base=root/'knowledge/raw/market_data/polymarket_neg_risk_manifests'
if not base.exists():
    raise SystemExit('manifest_dir_missing')
files=[p for p in base.iterdir() if p.is_file() and p.suffix=='.json']
files.sort(key=lambda p:p.stat().st_mtime)
if len(files)<2:
    raise SystemExit('need_two_manifests')
old_path=files[-2]
new_path=files[-1]
old=json.loads(old_path.read_text(encoding='utf-8'))
new=json.loads(new_path.read_text(encoding='utf-8'))

def extract(data):
    groups=data.get('groups') or data.get('eligible_groups') or tuple()
    out=dict()
    if isinstance(groups,dict):
        iterable=groups.values()
    else:
        iterable=groups
    for row in iterable:
        if not isinstance(row,dict):
            continue
        gid=str(row.get('group_id') or row.get('id') or row.get('event_id') or row.get('negRiskMarketID') or '')
        if not gid:
            continue
        title=str(row.get('title') or row.get('event_title') or row.get('question') or '')
        markets=row.get('markets') or tuple()
        count=row.get('market_count')
        if count is None:
            try:
                count=len(markets)
            except Exception:
                count=None
        out[gid]=dict(title=title,market_count=count,row=row)
    return out

old_groups=extract(old)
new_groups=extract(new)
print('OLD_MANIFEST',old_path.name)
print('NEW_MANIFEST',new_path.name)
print('OLD_GROUP_COUNT',len(old_groups))
print('NEW_GROUP_COUNT',len(new_groups))

added=sorted(set(new_groups)-set(old_groups),key=lambda x:int(x) if x.isdigit() else x)
removed=sorted(set(old_groups)-set(new_groups),key=lambda x:int(x) if x.isdigit() else x)
changed=list()
for gid in sorted(set(old_groups)&set(new_groups),key=lambda x:int(x) if x.isdigit() else x):
    a=old_groups.get(gid) or dict()
    b=new_groups.get(gid) or dict()
    if a.get('title')!=b.get('title') or a.get('market_count')!=b.get('market_count'):
        changed.append(gid)

for gid in sorted(new_groups,key=lambda x:int(x) if x.isdigit() else x):
    row=new_groups.get(gid) or dict()
    print('GROUP',gid,row.get('market_count'),row.get('title'))
print('ADDED_COUNT',len(added))
for gid in added:
    row=new_groups.get(gid) or dict()
    print('ADDED',gid,row.get('market_count'),row.get('title'))
print('REMOVED_COUNT',len(removed))
for gid in removed:
    row=old_groups.get(gid) or dict()
    print('REMOVED',gid,row.get('market_count'),row.get('title'))
print('CHANGED_COUNT',len(changed))
for gid in changed:
    a=old_groups.get(gid) or dict()
    b=new_groups.get(gid) or dict()
    print('CHANGED',gid,'OLD_COUNT',a.get('market_count'),'NEW_COUNT',b.get('market_count'),'OLD_TITLE',a.get('title'),'NEW_TITLE',b.get('title'))
print('IDENTICAL_GROUP_SET',set(old_groups)==set(new_groups))
print('NEG_RISK_MANIFEST_DIFF_PASS')
