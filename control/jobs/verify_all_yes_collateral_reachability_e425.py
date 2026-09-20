from pathlib import Path
import json

root=Path.cwd()
archive=root/'knowledge/raw/reference/polymarket_negrisk_adapter'
if not archive.exists():
    raise SystemExit('archive_missing')

wanted=[
    'docs__NegRiskAdapter.md',
    'src__NegRiskAdapter.sol',
    'src__interfaces__INegRiskAdapter.sol',
    'src__test__NegRiskAdapter__ConvertPositions.t.sol',
    'src__test__NegRiskAdapter__MergePositions.t.sol',
    'src__test__NegRiskAdapter__SplitPosition.t.sol',
    'README.md'
]

sources=dict()
for suffix in wanted:
    matches=[p for p in archive.iterdir() if p.is_file() and p.name.endswith(suffix)]
    matches.sort(key=lambda p:p.stat().st_mtime)
    if matches:
        sources[suffix]=matches[-1]

print('SOURCE_COUNT',len(sources))
for suffix,path in sources.items():
    print('SOURCE',suffix,path)

terms=[
    'function mergePositions',
    'function splitPosition',
    'function convertPositions',
    'mergePositions(',
    'splitPosition(',
    'convertPositions(',
    'burn',
    'safeTransferFrom',
    'transferFrom',
    'conditionalTokens.mergePositions',
    'conditionalTokens.splitPosition'
]

findings=list()
for suffix,path in sources.items():
    text=path.read_text(encoding='utf-8',errors='replace')
    lines=text.splitlines()
    for index,line in enumerate(lines):
        if any(term in line for term in terms):
            start=max(0,index-8)
            end=min(len(lines),index+18)
            block=lines[start:end]
            finding=dict(source=suffix,start_line=start+1,end_line=end,lines=block)
            findings.append(finding)
            print('MATCH_BEGIN',suffix,'LINES',start+1,end)
            for line_number in range(start,end):
                print('LINE',line_number+1,lines[line_number][:1600])
            print('MATCH_END')

adapter=None
for suffix,path in sources.items():
    if suffix=='src__NegRiskAdapter.sol':
        adapter=path.read_text(encoding='utf-8',errors='replace')
        break
if adapter is None:
    raise SystemExit('adapter_source_missing')

has_merge='function mergePositions' in adapter
has_split='function splitPosition' in adapter
has_convert='function convertPositions' in adapter
has_all_yes_function=False
for phrase in ['mergeYes','mergeYES','allYes','allYES','mergeMarket','redeemMarket','convertYes','convertYES']:
    if phrase in adapter:
        has_all_yes_function=True

print('HAS_MERGE_POSITIONS',has_merge)
print('HAS_SPLIT_POSITION',has_split)
print('HAS_CONVERT_POSITIONS',has_convert)
print('HAS_EXPLICIT_ALL_YES_FUNCTION',has_all_yes_function)

reasoning=list()
reasoning.append('Initial inventory: YES token for every question, zero NO tokens, zero extra collateral.')
reasoning.append('mergePositions requires a YES and NO complete pair for one binary condition if implementation and tests confirm that input structure.')
reasoning.append('convertPositions is relevant only if its implementation consumes NO positions.')
reasoning.append('splitPosition requires collateral input and therefore does not extract collateral from an all-YES-only inventory.')
reasoning.append('If no function consumes an all-YES market-wide set, the all-YES payoff equivalence is settlement-value equivalence rather than pre-resolution collateral reachability.')
for row in reasoning:
    print('REASONING',row)

out=archive/'e425-all-yes-collateral-reachability.json'
payload=dict(source_files=dict((key,str(value)) for key,value in sources.items()),finding_count=len(findings),findings=findings,has_merge_positions=has_merge,has_split_position=has_split,has_convert_positions=has_convert,has_explicit_all_yes_function=has_all_yes_function,reasoning=reasoning,live_trading=False,paid_actions=False,wallet_actions=False)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')
print('OUTPUT_PATH',out)
print('ALL_YES_COLLATERAL_REACHABILITY_E425_PASS')
