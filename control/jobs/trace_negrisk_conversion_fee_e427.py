from pathlib import Path
from urllib.request import Request,urlopen
import json

root=Path.cwd()
archive=root/'knowledge/raw/reference/polymarket_negrisk_adapter'
if not archive.exists():
    raise SystemExit('adapter_archive_missing')

adapter_files=[p for p in archive.iterdir() if p.is_file() and p.name.endswith('src__NegRiskAdapter.sol')]
adapter_files.sort(key=lambda p:p.stat().st_mtime)
if not adapter_files:
    raise SystemExit('adapter_source_missing')
adapter_path=adapter_files[-1]
adapter_text=adapter_path.read_text(encoding='utf-8',errors='replace')
adapter_lines=adapter_text.splitlines()

print('ADAPTER_SOURCE',adapter_path)
for index,line in enumerate(adapter_lines):
    low=line.lower()
    if 'feebips' in low or 'getmarketdata' in low or 'preparemarket' in low or 'fee_denominator' in low:
        start=max(0,index-4)
        end=min(len(adapter_lines),index+7)
        print('ADAPTER_MATCH_BEGIN',start+1,end)
        for number in range(start,end):
            print('LINE',number+1,adapter_lines[number][:1600])
        print('ADAPTER_MATCH_END')

repro_dir=root/'knowledge/raw/market_data/polymarket_reproductions'
repros=[p for p in repro_dir.iterdir() if p.is_file() and p.name.endswith('-anthropic-548858-e420.json')]
repros.sort(key=lambda p:p.stat().st_mtime)
if not repros:
    raise SystemExit('e420_missing')
repro=json.loads(repros[-1].read_text(encoding='utf-8'))
event_sha=str(repro.get('event_sha256') or '')
event_path=Path.home()/'.local/state/prediction-research/raw/polymarket_gamma_events'/(event_sha+'.json')
if not event_path.exists():
    raise SystemExit('event_raw_missing')
event=json.loads(event_path.read_text(encoding='utf-8'))

print('EVENT_SOURCE',event_path)
print('EVENT_ID',event.get('id'))
print('NEG_RISK_MARKET_ID',event.get('negRiskMarketID'))

def walk(value,path):
    rows=list()
    if isinstance(value,dict):
        for key,item in value.items():
            key_text=str(key)
            child=path+'.'+key_text if path else key_text
            low=key_text.lower()
            if 'fee' in low or 'negrisk' in low or 'adapter' in low or 'contract' in low:
                preview=item
                if isinstance(item,(dict,list)):
                    preview=str(item)[:1000]
                rows.append((child,preview))
            rows.extend(walk(item,child))
    elif isinstance(value,list):
        for index,item in enumerate(value):
            rows.extend(walk(item,path+'['+str(index)+']'))
    return rows

field_rows=walk(event,'event')
seen=set()
for path,value in field_rows:
    key=(path,str(value))
    if key in seen:
        continue
    seen.add(key)
    print('EVENT_FIELD',path,'VALUE',str(value)[:1400])

all_files=[p for p in archive.iterdir() if p.is_file()]
for p in sorted(all_files,key=lambda x:x.name):
    try:
        text=p.read_text(encoding='utf-8',errors='replace')
    except Exception:
        continue
    lines=text.splitlines()
    for index,line in enumerate(lines):
        low=line.lower()
        if 'feebips' in low or 'getmarketdata' in low:
            print('ARCHIVE_REFERENCE',p.name,'LINE',index+1,line[:1600])

market_data_paths=list()
trees=[p for p in archive.iterdir() if p.is_file() and p.name.endswith('-tree.json')]
trees.sort(key=lambda p:p.stat().st_mtime)
if trees:
    tree=json.loads(trees[-1].read_text(encoding='utf-8'))
    for item in tree.get('tree') or tuple():
        if not isinstance(item,dict):
            continue
        path=str(item.get('path') or '')
        low=path.lower()
        if 'marketdata' in low or 'market_data' in low:
            market_data_paths.append(path)

market_data_paths=sorted(set(market_data_paths))
print('MARKET_DATA_PATH_COUNT',len(market_data_paths))
for path in market_data_paths:
    print('MARKET_DATA_PATH',path)

raw_base='https:'+chr(47)+chr(47)+'raw.githubusercontent.com/Polymarket/neg-risk-ctf-adapter/main/'
fetched=list()
for path in market_data_paths[:20]:
    try:
        req=Request(raw_base+path,headers={'User-Agent':'PredictionEdgeHunter/1.0'})
        with urlopen(req,timeout=30) as response:
            raw=response.read()
            status=response.status
    except Exception as exc:
        print('FETCH_FAILED',path,str(exc)[:300])
        continue
    if status!=200:
        continue
    text=raw.decode('utf-8',errors='replace')
    out=archive/('e427__'+path.replace(chr(47),'__'))
    out.write_bytes(raw)
    fetched.append(path)
    for index,line in enumerate(text.splitlines()):
        low=line.lower()
        if 'feebips' in low or 'getmarketdata' in low or 'marketdata' in low:
            print('FETCHED_REFERENCE',path,'LINE',index+1,line[:1600])

print('FETCHED_MARKET_DATA_FILES',len(fetched))
print('CONVERSION_FORMULA_PRESENT', 'md.feeBips()' in adapter_text)
print('GAMMA_FEE_RELATED_FIELD_COUNT',len(field_rows))
print('TRACE_NEGRISK_CONVERSION_FEE_E427_PASS')
