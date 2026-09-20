from pathlib import Path
import json

root=Path.cwd()
archive=root/'knowledge/raw/reference/polymarket_negrisk_adapter'
if not archive.exists():
    raise SystemExit('archive_missing')

wanted=['MarketData.sol','MarketDataManager.sol','StorageHelper.sol','INegRiskAdapter.sol']
selected=dict()
for name in wanted:
    matches=[p for p in archive.iterdir() if p.is_file() and p.name.endswith(name)]
    matches.sort(key=lambda p:p.stat().st_mtime)
    if matches:
        selected[name]=matches[-1]

print('SOURCE_COUNT',len(selected))
for name,path in selected.items():
    print('SOURCE',name,path)

needles=['type MarketData','struct MarketData','function feeBips','function questionCount','function oracle','function getMarketData','mapping','marketData','MarketData.wrap','MarketData.unwrap','FEE','QUESTION_COUNT']
findings=list()
for name,path in selected.items():
    text=path.read_text(encoding='utf-8',errors='replace')
    lines=text.splitlines()
    printed=set()
    for index,line in enumerate(lines):
        if any(needle in line for needle in needles):
            start=max(0,index-5)
            end=min(len(lines),index+12)
            key=(start,end)
            if key in printed:
                continue
            printed.add(key)
            block=lines[start:end]
            findings.append(dict(source=name,start_line=start+1,end_line=end,lines=block))
            print('MATCH_BEGIN',name,'LINES',start+1,end)
            for number in range(start,end):
                print('LINE',number+1,lines[number][:1800])
            print('MATCH_END')

manager_text=''
market_text=''
for name,path in selected.items():
    if name=='MarketDataManager.sol':
        manager_text=path.read_text(encoding='utf-8',errors='replace')
    if name=='MarketData.sol':
        market_text=path.read_text(encoding='utf-8',errors='replace')

print('HAS_GET_MARKET_DATA', 'function getMarketData' in manager_text)
print('HAS_FEE_BIPS', 'function feeBips' in market_text)
print('HAS_MARKETDATA_UNWRAP', 'MarketData.unwrap' in market_text or 'unwrap' in market_text)
print('HAS_MARKETDATA_WRAP', 'MarketData.wrap' in manager_text or 'MarketData.wrap' in market_text)

out=archive/'e431-marketdata-layout.json'
payload=dict(source_files=dict((name,str(path)) for name,path in selected.items()),finding_count=len(findings),findings=findings,has_get_market_data=('function getMarketData' in manager_text),has_fee_bips=('function feeBips' in market_text),live_trading=False,paid_actions=False,wallet_actions=False)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')
print('OUTPUT_PATH',out)
print('NEGRISK_MARKETDATA_LAYOUT_E431_PASS')
