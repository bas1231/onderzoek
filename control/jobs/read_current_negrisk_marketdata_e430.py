from pathlib import Path
from urllib.request import Request,urlopen
import json

root=Path.cwd()
archive=root/'knowledge/raw/reference/polymarket_negrisk_adapter'
if not archive.exists():
    raise SystemExit('archive_missing')

adapter='0xd91e80cf2e7be2e162c6513ced06f1dd0da35296'
market_id='0x4bcf7372694cb3ed70e31369f7602502cf80c6194e348bcba13c20b0a8936400'
rpc_url='https:'+chr(47)+chr(47)+'polygon-bor-rpc.publicnode.com'

counter=0
def rpc(method,params):
    global counter
    counter+=1
    payload=json.dumps(dict(jsonrpc='2.0',id=counter,method=method,params=params)).encode()
    req=Request(rpc_url,data=payload,headers={'Content-Type':'application/json','User-Agent':'PredictionEdgeHunter/1.0'},method='POST')
    with urlopen(req,timeout=40) as response:
        raw=response.read()
        status=response.status
    if status!=200:
        raise RuntimeError('rpc_http_'+str(status))
    data=json.loads(raw)
    if data.get('error') is not None:
        raise RuntimeError('rpc_'+str(data.get('error')))
    return data.get('result')

chain_id=rpc('eth_chainId',[])
latest=rpc('eth_blockNumber',[])
code=rpc('eth_getCode',[adapter,'latest'])
print('CHAIN_ID',int(chain_id,16))
print('LATEST_BLOCK',int(latest,16))
print('ADAPTER_CODE_PRESENT',code not in ['0x','0x0',None])
print('ADAPTER_ADDRESS',adapter)
print('MARKET_ID',market_id)

matches=list()
trees=[p for p in archive.iterdir() if p.is_file() and p.name.endswith('-tree.json')]
trees.sort(key=lambda p:p.stat().st_mtime)
if not trees:
    raise SystemExit('tree_missing')
tree=json.loads(trees[-1].read_text(encoding='utf-8'))
raw_base='https:'+chr(47)+chr(47)+'raw.githubusercontent.com/Polymarket/neg-risk-ctf-adapter/main/'

sol_paths=list()
for item in tree.get('tree') or tuple():
    if not isinstance(item,dict):
        continue
    path=str(item.get('path') or '')
    if path.startswith('src/') and path.endswith('.sol'):
        sol_paths.append(path)

for path in sorted(set(sol_paths)):
    local_matches=[p for p in archive.iterdir() if p.is_file() and p.name.endswith(path.replace(chr(47),''))]
    text=None
    if local_matches:
        local_matches.sort(key=lambda p:p.stat().st_mtime)
        text=local_matches[-1].read_text(encoding='utf-8',errors='replace')
    else:
        try:
            req=Request(raw_base+path,headers={'User-Agent':'PredictionEdgeHunter/1.0'})
            with urlopen(req,timeout=30) as response:
                raw=response.read()
                status=response.status
            if status==200:
                text=raw.decode('utf-8',errors='replace')
                out=archive/('e430'+path.replace(chr(47),'__'))
                out.write_bytes(raw)
        except Exception:
            text=None
    if text is None:
        continue
    lines=text.splitlines()
    hit=False
    for index,line in enumerate(lines):
        low=line.lower()
        if 'marketdata' in low or 'feebips' in low or 'getmarketdata' in low:
            hit=True
            start=max(0,index-3)
            end=min(len(lines),index+5)
            print('SOURCE_MATCH_BEGIN',path,'LINES',start+1,end)
            for number in range(start,end):
                print('LINE',number+1,lines[number][:1800])
            print('SOURCE_MATCH_END')
    if hit:
        matches.append(path)

print('SOURCE_FILES_WITH_MARKETDATA',len(set(matches)))
for path in sorted(set(matches)):
    print('MARKETDATA_SOURCE',path)

signatures=['getMarketData(bytes32)','marketData(bytes32)','markets(bytes32)']
for signature in signatures:
    sig_hex='0x'+signature.encode().hex()
    try:
        digest=rpc('web3_sha3',[sig_hex])
    except Exception as exc:
        print('SIGNATURE_HASH_FAILED',signature,str(exc)[:300])
        continue
    selector=digest[2:10]
    calldata='0x'+selector+market_id[2:].rjust(64,'0')
    print('CALL_SIGNATURE',signature)
    print('CALL_SELECTOR','0x'+selector)
    try:
        result=rpc('eth_call',[dict(to=adapter,data=calldata),'latest'])
        print('CALL_SUCCESS',signature,True)
        print('CALL_RESULT',result)
        body=result[2:] if isinstance(result,str) and result.startswith('0x') else ''
        print('CALL_RESULT_BYTES',len(body)//2)
        if body and len(body)%64==0:
            words=[body[index:index+64] for index in range(0,len(body),64)]
            print('CALL_WORD_COUNT',len(words))
            for index,word in enumerate(words):
                print('CALL_WORD',index,'HEX','0x'+word,'UINT',int(word,16))
    except Exception as exc:
        print('CALL_SUCCESS',signature,False)
        print('CALL_ERROR',signature,str(exc)[:500])

print('CURRENT_NEGRISK_MARKETDATA_E430_PASS')
