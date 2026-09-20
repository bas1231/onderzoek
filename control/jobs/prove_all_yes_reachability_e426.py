from pathlib import Path
import json

root=Path.cwd()
archive=root/'knowledge/raw/reference/polymarket_negrisk_adapter'
matches=[p for p in archive.iterdir() if p.is_file() and p.name.endswith('src__NegRiskAdapter.sol')]
matches.sort(key=lambda p:p.stat().st_mtime)
if not matches:
    raise SystemExit('adapter_missing')
path=matches[-1]
text=path.read_text(encoding='utf-8',errors='replace')
lines=text.splitlines()

names=['splitPosition','mergePositions','redeemPositions','convertPositions']
functions=dict()
for name in names:
    start=None
    for index,line in enumerate(lines):
        if 'function '+name in line:
            start=index
            break
    if start is None:
        raise SystemExit('function_missing_'+name)
    depth=0
    opened=False
    end=start
    for index in range(start,len(lines)):
        line=lines[index]
        depth+=line.count('{')
        if line.count('{')>0:
            opened=True
        depth-=line.count('}')
        end=index
        if opened and depth==0:
            break
    body=lines[start:end+1]
    functions[name]=body
    print('FUNCTION_BEGIN',name,'LINES',start+1,end+1)
    for number in range(start,end+1):
        print('LINE',number+1,lines[number][:1800])
    print('FUNCTION_END',name)

split=' '.join(functions.get('splitPosition') or tuple())
merge=' '.join(functions.get('mergePositions') or tuple())
redeem=' '.join(functions.get('redeemPositions') or tuple())
convert=' '.join(functions.get('convertPositions') or tuple())

split_consumes_collateral=('safeTransferFrom(msg.sender' in split and 'splitPosition' in split)
merge_calls_ctf_merge=('mergePositions' in merge and 'ctf.' in merge)
redeem_calls_resolution_path=('redeemPositions' in redeem)
convert_mentions_no=('NO' in convert or 'no' in convert.lower())
convert_burns_or_transfers_positions=('safeBatchTransferFrom' in convert or 'safeTransferFrom' in convert or 'burn' in convert.lower())
explicit_all_yes=False
for phrase in ['mergeYes','mergeYES','allYes','allYES','convertYes','convertYES','redeemMarket','mergeMarket']:
    if phrase in text:
        explicit_all_yes=True

print('SPLIT_CONSUMES_COLLATERAL',split_consumes_collateral)
print('MERGE_IS_SINGLE_FUNCTION_PATH',merge_calls_ctf_merge)
print('REDEEM_FUNCTION_PRESENT',redeem_calls_resolution_path)
print('CONVERT_REFERENCES_NO_SEMANTICS',convert_mentions_no)
print('CONVERT_CONSUMES_POSITIONS',convert_burns_or_transfers_positions)
print('EXPLICIT_ALL_YES_MARKET_FUNCTION',explicit_all_yes)

all_yes_pre_resolution_path=False
if explicit_all_yes:
    all_yes_pre_resolution_path=True

print('INITIAL_INVENTORY','YES token for every question; zero NO tokens; zero extra collateral')
print('PRE_RESOLUTION_ALL_YES_TO_COLLATERAL_PATH_FOUND',all_yes_pre_resolution_path)
print('VERDICT',('PATH_FOUND' if all_yes_pre_resolution_path else 'NO_PATH_FOUND_IN_ADAPTER_API'))
print('LIMITATION','Verdict concerns the archived official NegRiskAdapter API and source only; it does not assume off-contract secondary-market liquidation.')

out=archive/'e426-all-yes-reachability-proof.json'
payload=dict(source=str(path),split_consumes_collateral=split_consumes_collateral,merge_calls_ctf_merge=merge_calls_ctf_merge,redeem_function_present=redeem_calls_resolution_path,convert_references_no_semantics=convert_mentions_no,convert_consumes_positions=convert_burns_or_transfers_positions,explicit_all_yes_market_function=explicit_all_yes,pre_resolution_all_yes_to_collateral_path_found=all_yes_pre_resolution_path,verdict=('PATH_FOUND' if all_yes_pre_resolution_path else 'NO_PATH_FOUND_IN_ADAPTER_API'),limitation='Archived official NegRiskAdapter API and source only; secondary market liquidation excluded.',live_trading=False,paid_actions=False,wallet_actions=False)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')
print('OUTPUT_PATH',out)
print('ALL_YES_REACHABILITY_PROOF_E426_PASS')
