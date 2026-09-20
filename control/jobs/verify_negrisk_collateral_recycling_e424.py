from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone
import hashlib
import json

root=Path.cwd()
agent='PredictionEdgeHunter/1.0'
base_api='https:'+chr(47)+chr(47)+'api.github.com/repos/Polymarket/neg-risk-ctf-adapter/git/trees/main?recursive=1'
req=Request(base_api,headers={'User-Agent':agent,'Accept':'application/vnd.github+json'})
with urlopen(req,timeout=30) as response:
    tree_raw=response.read()
    tree_status=response.status
if tree_status!=200:
    raise SystemExit('tree_fetch_failed')
tree=json.loads(tree_raw)

archive=root/'knowledge/raw/reference/polymarket_negrisk_adapter'
archive.mkdir(parents=True,exist_ok=True)
tree_sha=hashlib.sha256(tree_raw).hexdigest()
tree_path=archive/(tree_sha+'-tree.json')
if not tree_path.exists():
    tree_path.write_bytes(tree_raw)

paths=list()
for item in tree.get('tree') or tuple():
    if not isinstance(item,dict):
        continue
    path=str(item.get('path') or '')
    low=path.lower()
    if low.endswith('.md') or low.endswith('.sol'):
        if 'negrisk' in low or 'adapter' in low or low.endswith('readme.md'):
            paths.append(path)
paths=sorted(set(paths))

print('TREE_HTTP_STATUS',tree_status)
print('TREE_SHA256',tree_sha)
print('CANDIDATE_SOURCE_COUNT',len(paths))
for path in paths:
    print('SOURCE_PATH',path)

raw_base='https:'+chr(47)+chr(47)+'raw.githubusercontent.com/Polymarket/neg-risk-ctf-adapter/main/'
terms=['convert','merge','collateral','redeem','split','position','before resolution','pre-resolution','complete set','yes tokens','no tokens']
findings=list()

for path in paths:
    url=raw_base+path
    try:
        req=Request(url,headers={'User-Agent':agent})
        with urlopen(req,timeout=30) as response:
            raw=response.read()
            status=response.status
    except Exception as exc:
        print('SOURCE_FETCH_FAILED',path,str(exc)[:300])
        continue
    if status!=200:
        continue
    sha=hashlib.sha256(raw).hexdigest()
    safe_name=path.replace(chr(47),'__')
    out=archive/(sha+'-'+safe_name)
    if not out.exists():
        out.write_bytes(raw)
    text=raw.decode('utf-8',errors='replace')
    lines=text.splitlines()
    matched=set()
    for index,line in enumerate(lines):
        low=line.lower()
        if any(term in low for term in terms):
            start=max(0,index-2)
            end=min(len(lines),index+3)
            key=(start,end)
            if key in matched:
                continue
            matched.add(key)
            block=lines[start:end]
            finding=dict(path=path,start_line=start+1,end_line=end,lines=block)
            findings.append(finding)
            print('MATCH_BEGIN',path,'LINES',start+1,end)
            for line_number in range(start,end):
                print('LINE',line_number+1,lines[line_number][:1200])
            print('MATCH_END')

function_terms=['convertPositions','mergePositions','splitPosition','redeemPositions','convert','merge']
function_hits=list()
for finding in findings:
    joined=' '.join(finding.get('lines') or tuple())
    for term in function_terms:
        if term in joined:
            function_hits.append(dict(term=term,path=finding.get('path'),start_line=finding.get('start_line'),end_line=finding.get('end_line'),lines=finding.get('lines')))

print('FINDING_COUNT',len(findings))
print('FUNCTION_HIT_COUNT',len(function_hits))
for hit in function_hits:
    print('FUNCTION_HIT',hit.get('term'),'PATH',hit.get('path'),'LINES',hit.get('start_line'),hit.get('end_line'))
    for line in hit.get('lines') or tuple():
        print('FUNCTION_LINE',line[:1200])

stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out=archive/(stamp+'-e424-summary.json')
payload=dict(retrieved_at=datetime.now(timezone.utc).isoformat(),repository='Polymarket/neg-risk-ctf-adapter',tree_sha256=tree_sha,source_paths=paths,finding_count=len(findings),findings=findings,function_hits=function_hits,live_trading=False,paid_actions=False,wallet_actions=False)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')
print('OUTPUT_PATH',out)
print('NEGRISK_COLLATERAL_RECYCLING_RESEARCH_E424_PASS')
