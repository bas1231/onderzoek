from pathlib import Path
from urllib.request import Request,urlopen
import hashlib
import json

root=Path.cwd()
archive=root/'knowledge/raw/reference/polymarket_negrisk_adapter'
if not archive.exists():
    raise SystemExit('archive_missing')

trees=[p for p in archive.iterdir() if p.is_file() and p.name.endswith('-tree.json')]
trees.sort(key=lambda p:p.stat().st_mtime)
if not trees:
    raise SystemExit('tree_missing')
tree=json.loads(trees[-1].read_text(encoding='utf-8'))

terms=['marketdata','market_data','getmarketdata','marketdatalib','storage','datatypes']
paths=list()
for item in tree.get('tree') or tuple():
    if not isinstance(item,dict):
        continue
    path=str(item.get('path') or '')
    low=path.lower()
    if not (low.endswith('.sol') or low.endswith('.json')):
        continue
    if any(term in low for term in terms):
        paths.append(path)

for item in tree.get('tree') or tuple():
    if not isinstance(item,dict):
        continue
    path=str(item.get('path') or '')
    low=path.lower()
    if low.endswith('.sol') and ('negriskadapter' in low or 'negriskidlib' in low):
        paths.append(path)

paths=sorted(set(paths))
print('CANDIDATE_PATH_COUNT',len(paths))
for path in paths:
    print('CANDIDATE_PATH',path)

raw_base='https:'+chr(47)+chr(47)+'raw.githubusercontent.com/Polymarket/neg-risk-ctf-adapter/main/'
source_files=list()
for path in paths:
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
    sha=hashlib.sha256(raw).hexdigest()
    out=archive/(sha+'-e430-'+path.replace(chr(47),'__'))
    if not out.exists():
        out.write_bytes(raw)
    source_files.append((path,out,raw.decode('utf-8',errors='replace')))

print('FETCHED_SOURCE_COUNT',len(source_files))

needles=['getMarketData','MarketData','feeBips','questionCount','oracle','mapping','prepareMarket']
findings=list()
for path,out,text in source_files:
    lines=text.splitlines()
    for index,line in enumerate(lines):
        if any(needle in line for needle in needles):
            start=max(0,index-5)
            end=min(len(lines),index+12)
            block=lines[start:end]
            finding=dict(path=path,start_line=start+1,end_line=end,lines=block)
            findings.append(finding)
            print('MATCH_BEGIN',path,'LINES',start+1,end)
            for number in range(start,end):
                print('LINE',number+1,lines[number][:1800])
            print('MATCH_END')

signatures=set()
for path,out,text in source_files:
    for line in text.splitlines():
        stripped=line.strip()
        if 'function getMarketData' in stripped:
            signatures.add(stripped)
        if 'getMarketData(' in stripped and ('external' in stripped or 'public' in stripped or 'view' in stripped):
            signatures.add(stripped)

print('GET_MARKET_DATA_SIGNATURE_COUNT',len(signatures))
for signature in sorted(signatures):
    print('GET_MARKET_DATA_SIGNATURE',signature)

struct_lines=list()
for path,out,text in source_files:
    lines=text.splitlines()
    for index,line in enumerate(lines):
        if 'struct MarketData' in line or 'type MarketData' in line:
            start=max(0,index-2)
            end=min(len(lines),index+20)
            struct_lines.append(dict(path=path,start_line=start+1,end_line=end,lines=lines[start:end]))
            print('MARKET_DATA_DEFINITION_BEGIN',path,'LINES',start+1,end)
            for number in range(start,end):
                print('LINE',number+1,lines[number][:1800])
            print('MARKET_DATA_DEFINITION_END')

out=archive/'e430-marketdata-abi-resolution.json'
payload=dict(source_tree=str(trees[-1]),candidate_paths=paths,fetched_paths=[row[0] for row in source_files],get_market_data_signatures=sorted(signatures),market_data_definitions=struct_lines,finding_count=len(findings),findings=findings,live_trading=False,paid_actions=False,wallet_actions=False)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')
print('OUTPUT_PATH',out)
print('MARKETDATA_ABI_RESOLUTION_E430_PASS')
