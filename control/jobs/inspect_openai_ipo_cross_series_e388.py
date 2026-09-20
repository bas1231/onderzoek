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

targets={'48292','200252'}
found=dict()
for p in files:
    try:
        data=json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        continue
    for row in data.get('groups') or tuple():
        if not isinstance(row,dict):
            continue
        eid=str(row.get('event_id') or '')
        if eid in targets:
            found[eid]=dict(row=row,manifest=p.name)

print('FOUND_COUNT',len(found))
for eid in ['48292','200252']:
    item=found.get(eid)
    if not isinstance(item,dict):
        print('MISSING_EVENT',eid)
        continue
    row=item.get('row') or dict()
    print('EVENT',eid)
    print('MANIFEST',item.get('manifest'))
    print('TITLE',row.get('title'))
    print('NEG_RISK_MARKET_ID',row.get('neg_risk_market_id'))
    print('MARKET_COUNT',row.get('market_count'))
    markets=row.get('markets') or tuple()
    for index,market in enumerate(markets):
        if not isinstance(market,dict):
            continue
        print('MARKET_INDEX',index)
        print('MARKET_ID',market.get('market_id'))
        print('QUESTION',market.get('question'))
        print('YES_TOKEN',market.get('yes_token'))
        print('NO_TOKEN',market.get('no_token'))
    print('---')
print('OPENAI_IPO_CROSS_SERIES_INSPECT_PASS')
