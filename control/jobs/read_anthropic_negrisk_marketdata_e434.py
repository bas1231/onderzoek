from urllib.request import Request,urlopen
from datetime import datetime,timezone
from pathlib import Path
import json

root=Path.cwd()
rpc='https:'+chr(47)+chr(47)+'polygon-bor-rpc.publicnode.com'
adapter='0xd91e80cf2e7be2e162c6513ced06f1dd0da35296'
market_id='0x4bcf7372694cb3ed70e31369f7602502cf80c6194e348bcba13c20b0a8936400'

def rpc_call(method,params):
    body=json.dumps(dict(jsonrpc='2.0',id=1,method=method,params=params)).encode()
    req=Request(rpc,data=body,headers={'Content-Type':'application/json','User-Agent':'PredictionEdgeHunter/1.0'},method='POST')
    with urlopen(req,timeout=30) as response:
        raw=response.read()
        status=response.status
    if status!=200:
        raise SystemExit('rpc_http_'+str(status))
    data=json.loads(raw)
    if data.get('error') is not None:
        raise SystemExit('rpc_error_'+str(data.get('error')))
    return data.get('result')

def selector(signature):
    encoded='0x'+signature.encode().hex()
    digest=rpc_call('web3_sha3',[encoded])
    if not isinstance(digest,str) or not digest.startswith('0x') or len(digest)<10:
        raise SystemExit('selector_hash_bad_'+signature)
    return digest[2:10]

def eth_call(signature):
    sel=selector(signature)
    argument=market_id[2:].rjust(64,'0')
    data='0x'+sel+argument
    result=rpc_call('eth_call',[dict(to=adapter,data=data),'latest'])
    print('CALL',signature,'SELECTOR','0x'+sel,'RAW_RESULT',result)
    return result

code=rpc_call('eth_getCode',[adapter,'latest'])
block_hex=rpc_call('eth_blockNumber',[])
if not isinstance(code,str) or code in ['0x','0x0']:
    raise SystemExit('adapter_code_missing')
block_number=int(block_hex,16)
print('RPC',rpc)
print('LATEST_BLOCK',block_number)
print('ADAPTER',adapter)
print('ADAPTER_CODE_BYTES',(len(code)-2)//2)
print('MARKET_ID',market_id)

fee_raw=eth_call('getFeeBips(bytes32)')
count_raw=eth_call('getQuestionCount(bytes32)')
oracle_raw=eth_call('getOracle(bytes32)')

fee_bips=int(fee_raw,16)
question_count=int(count_raw,16)
oracle='0x'+oracle_raw[-40:] if isinstance(oracle_raw,str) and len(oracle_raw)>=42 else None
fee_rate=fee_bips/10000.0

print('FEE_BIPS',fee_bips)
print('CONVERSION_FEE_RATE',fee_rate)
print('QUESTION_COUNT',question_count)
print('ORACLE',oracle)
print('QUESTION_COUNT_MATCH_ANTHROPIC',question_count==10)
print('MARKET_PREPARED',oracle is not None and oracle!='0x0000000000000000000000000000000000000000')

outdir=root/'knowledge/raw/reference/polymarket_negrisk_adapter'
outdir.mkdir(parents=True,exist_ok=True)
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out=outdir/(stamp+'-anthropic-marketdata-e434.json')
payload=dict(retrieved_at=datetime.now(timezone.utc).isoformat(),rpc=rpc,latest_block=block_number,adapter=adapter,market_id=market_id,fee_bips=fee_bips,conversion_fee_rate=fee_rate,question_count=question_count,oracle=oracle,question_count_matches_anthropic=(question_count==10),market_prepared=(oracle is not None and oracle!='0x0000000000000000000000000000000000000000'),live_trading=False,paid_actions=False,wallet_actions=False)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')
print('OUTPUT_PATH',out)
print('ANTHROPIC_NEGRISK_MARKETDATA_E434_PASS')
