from pathlib import Path
import json

root=Path.cwd()
archive=root/'knowledge/raw/reference/polymarket_negrisk_adapter'
if not archive.exists():
    raise SystemExit('archive_missing')

files=[p for p in archive.iterdir() if p.is_file()]
terms=['MarketData','feeBips','questionCount','oracle','getMarketData','setMarketData','marketData']
findings=list()

for path in sorted(files,key=lambda p:p.name):
    try:
        text=path.read_text(encoding='utf-8',errors='replace')
    except Exception:
        continue
    lines=text.splitlines()
    matched=False
    for index,line in enumerate(lines):
        if any(term in line for term in terms):
            matched=True
            start=max(0,index-5)
            end=min(len(lines),index+10)
            block=lines[start:end]
            findings.append(dict(file=path.name,start_line=start+1,end_line=end,lines=block))
            print('MATCH_BEGIN',path.name,'LINES',start+1,end)
            for number in range(start,end):
                print('LINE',number+1,lines[number][:1800])
            print('MATCH_END')
    if matched:
        print('MATCHED_FILE',path.name)

print('FINDING_COUNT',len(findings))

candidate_files=list()
for path in sorted(files,key=lambda p:p.name):
    low=path.name.lower()
    if 'marketdata' in low or 'market_data' in low or 'storage' in low or 'library' in low or 'negriskid' in low:
        candidate_files.append(path.name)
print('CANDIDATE_LAYOUT_FILES',len(candidate_files))
for name in candidate_files:
    print('CANDIDATE_FILE',name)

summary=archive/'e433-marketdata-layout-findings.json'
payload=dict(finding_count=len(findings),candidate_layout_files=candidate_files,findings=findings,live_trading=False,paid_actions=False,wallet_actions=False)
summary.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')
print('OUTPUT_PATH',summary)
print('NEGRISK_MARKETDATA_LAYOUT_E433_PASS')
