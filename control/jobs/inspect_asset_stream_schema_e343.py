from pathlib import Path
import json

root=Path.cwd()
p=root/'knowledge/raw/market_data/polymarket_shadow_smoke/20260920T021521Z106981.jsonl'
if not p.exists():
    raise SystemExit('smoke_archive_missing')

counts=dict()
examples=dict()
assets=set()
lines=0
for raw_line in p.read_text(encoding='utf-8').splitlines():
    if not raw_line.strip():
        continue
    lines+=1
    outer=json.loads(raw_line)
    raw=outer.get('raw')
    if raw=='PONG':
        counts['PONG']=counts.get('PONG',0)+1
        continue
    if not isinstance(raw,str):
        counts['NON_TEXT']=counts.get('NON_TEXT',0)+1
        continue
    try:
        parsed=json.loads(raw)
    except Exception:
        counts['NON_JSON']=counts.get('NON_JSON',0)+1
        continue
    items=parsed if isinstance(parsed,list) else [parsed]
    for item in items:
        if not isinstance(item,dict):
            counts['NON_OBJECT']=counts.get('NON_OBJECT',0)+1
            continue
        kind=str(item.get('event_type') or item.get('type') or 'UNKNOWN')
        counts[kind]=counts.get(kind,0)+1
        asset=item.get('asset_id') or item.get('assetId')
        if asset:
            assets.add(str(asset))
        if kind not in examples:
            examples[kind]=item

print('ARCHIVE',p.name)
print('LINE_COUNT',lines)
print('ASSET_COUNT',len(assets))
for kind in sorted(counts):
    print('COUNT',kind,counts.get(kind))
for kind in sorted(examples):
    item=examples.get(kind) or dict()
    print('EVENT_TYPE',kind)
    print('TOP_LEVEL_KEYS',sorted(item.keys()))
    for key in sorted(item.keys()):
        value=item.get(key)
        if isinstance(value,list):
            print('FIELD',key,'LIST_LEN',len(value))
            if value:
                first=value[0]
                if isinstance(first,dict):
                    print('FIELD_FIRST_KEYS',key,sorted(first.keys()))
                    print('FIELD_FIRST_SAMPLE',key,json.dumps(first,sort_keys=True)[:2000])
                else:
                    print('FIELD_FIRST_SAMPLE',key,str(first)[:1000])
        elif isinstance(value,dict):
            print('FIELD',key,'OBJECT_KEYS',sorted(value.keys()))
            print('FIELD_SAMPLE',key,json.dumps(value,sort_keys=True)[:2000])
        else:
            print('FIELD',key,str(value)[:2000])
    print('---')
print('HAS_LAST_TRADE_PRICE','last_trade_price' in counts)
print('HAS_PRICE_CHANGE','price_change' in counts)
print('ASSET_STREAM_SCHEMA_INSPECTION_PASS')
