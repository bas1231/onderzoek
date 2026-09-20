from pathlib import Path
import json

root=Path.cwd()
archive=root/'knowledge/raw/reference/polymarket_negrisk_adapter'

suffixes=[
    'e430-src__modules__MarketDataManager.sol',
    'e430-src__types__MarketData.sol',
    'e430-src__dev__StorageHelper.sol',
    'e430-src__interfaces__INegRiskAdapter.sol',
    'src__NegRiskAdapter.sol'
]

sources=dict()
for suffix in suffixes:
    matches=[p for p in archive.iterdir() if p.is_file() and p.name.endswith(suffix)]
    matches.sort(key=lambda p:p.stat().st_mtime)
    if matches:
        sources[suffix]=matches[-1]

if not sources:
    raise SystemExit('sources_missing')

print('SOURCE_COUNT',len(sources))
for key,path in sources.items():
    print('SOURCE',key,path)

needles=[
    'getMarketData',
    'marketData',
    'MarketData',
    'mapping',
    'storage',
    'sload',
    'slot',
    '_markets',
    'markets'
]

findings=list()
for key,path in sources.items():
    text=path.read_text(encoding='utf-8',errors='replace')
    lines=text.splitlines()
    printed=set()
    for index,line in enumerate(lines):
        if any(needle in line for needle in needles):
            start=max(0,index-5)
            end=min(len(lines),index+10)
            marker=(start,end)
            if marker in printed:
                continue
            printed.add(marker)
            block=lines[start:end]
            findings.append(dict(source=key,start_line=start+1,end_line=end,lines=block))
            print('MATCH_BEGIN',key,'LINES',start+1,end)
            for number in range(start,end):
                print('LINE',number+1,lines[number][:1800])
            print('MATCH_END')

manager_text=''
for key,path in sources.items():
    if key.endswith('MarketDataManager.sol'):
        manager_text=path.read_text(encoding='utf-8',errors='replace')
        break

has_getter='getMarketData' in manager_text
has_mapping='mapping' in manager_text
has_public='public' in manager_text
has_external='external' in manager_text
has_internal='internal' in manager_text

print('MANAGER_HAS_GETMARKETDATA',has_getter)
print('MANAGER_HAS_MAPPING',has_mapping)
print('MANAGER_HAS_PUBLIC_TOKEN',has_public)
print('MANAGER_HAS_EXTERNAL_TOKEN',has_external)
print('MANAGER_HAS_INTERNAL_TOKEN',has_internal)

function_names=list()
if manager_text:
    for line in manager_text.splitlines():
        stripped=line.strip()
        if stripped.startswith('function '):
            head=stripped.split('(')[0]
            name=head.replace('function ','').strip()
            function_names.append(name)
            print('MANAGER_FUNCTION',name,'DECL',stripped[:1800])

out=archive/'e432-negrisk-marketdata-getter-layout.json'
payload=dict(source_files=dict((key,str(path)) for key,path in sources.items()),finding_count=len(findings),findings=findings,manager_has_getmarketdata=has_getter,manager_has_mapping=has_mapping,manager_has_public_token=has_public,manager_has_external_token=has_external,manager_has_internal_token=has_internal,manager_function_names=function_names,live_trading=False,paid_actions=False,wallet_actions=False)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')
print('OUTPUT_PATH',out)
print('NEGRISK_MARKETDATA_GETTER_LAYOUT_E432_PASS')
