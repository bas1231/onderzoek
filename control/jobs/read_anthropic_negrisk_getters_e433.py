from pathlib import Path
from datetime import datetime,timezone
from urllib.request import Request,urlopen
import json

root=Path.cwd()
adapter='0xd91e80cf2e7be2e162c6513ced06f1dd0da35296'
market_id='0x4bcf7372694cb3ed70e31369f7602502cf80c6194e348bcba13c20b0a8936400'

rpcs=[
    'https:'+chr(47)+chr(47)+'polygon-bor-rpc.publicnode.com',
    'https:'+chr(47)+chr(47)+'polygon-rpc.com'
]

def rpc_call(url,method,params):
    payload=json.dumps(dict(jsonrpc='2.0',id=1,method=method,params=params)).encode()
    req=Request(url,data=payload,headers={'Content-Type':'application/json','User-Agent':'PredictionEdgeHunter/1.0'},method='POST')
    with urlopen(req,timeout=30) as response:
        raw=response.read()
        status=response.status
    if status!=200:
        raise RuntimeError('http_'+str(status))
    data=json.loads(raw)
    if data.get('error') is not None:
        raise RuntimeError('rpc_'+str(data.get('error')))
    return data.get('result')

rpc=None
latest=None
for candidate in rpcs:
    try:
        latest=rpc_call(candidate,'eth_blockNumber',tuple())
        rpc=candidate
        print('RPC_OK',candidate,'LATEST_BLOCK',int(latest,16))
        break
    except Exception as exc:
        print('RPC_FAILED',candidate,str(exc)[:300])
if rpc is None:
    raise SystemExit('no_rpc_available')

code=rpc_call(rpc,'eth_getCode',[adapter,'latest'])
print('ADAPTER',adapter)
print('ADAPTER_CODE_PRESENT',isinstance(code,str) and len(code)>2)
print('ADAPTER_CODE_BYTES',(len(code)-2)//2 if isinstance(code,str) and code.startswith('0x') else None)
if not isinstance(code,str) or len(code)<=2:
    raise SystemExit('adapter_code_missing')

signatures=[
    ('getFeeBips(bytes32)','fee_bips'),
    ('getQuestionCount(bytes32)','question_count'),
    ('getOracle(bytes32)','oracle')
]

selectors=dict()
for signature,label in signatures:
    sig_hex='0x'+signature.encode().hex()
    digest=rpc_call(rpc,'web3_sha3',[sig_hex])
    if not isinstance(digest,str) or len(digest)<10:
        raise SystemExit('selector_hash_failed_'+label)
    selector=digest[2:10]
    selectors[label]=selector
    print('SELECTOR',label,selector)

arg=market_id[2:]
if len(arg)!=64:
    raise SystemExit('market_id_not_bytes32')

values=dict()
for label in ['fee_bips','question_count','oracle']:
    selector=selectors.get(label)
    calldata='0x'+selector+arg
    result=rpc_call(rpc,'eth_call',[dict(to=adapter,data=calldata),'latest'])
    print('RAW_RESULT',label,result)
    if not isinstance(result,str) or not result.startswith('0x'):
        raise SystemExit('bad_eth_call_'+label)
    if label in ['fee_bips','question_count']:
        value=int(result,16)
    else:
        raw=result[2:].rjust(64,'0')
        value='0x'+raw[-40:]
    values[label]=value
    print('DECODED',label,value)

fee_bips=int(values.get('fee_bips'))
question_count=int(values.get('question_count'))
oracle=str(values.get('oracle'))
fee_rate=fee_bips/10000.0

print('MARKET_ID',market_id)
print('QUESTION_COUNT',question_count)
print('FEE_BIPS',fee_bips)
print('CONVERSION_FEE_RATE',fee_rate)
print('ORACLE',oracle)
print('QUESTION_COUNT_MATCH_EXPECTED_10',question_count==10)
print('ORACLE_NONZERO',oracle!='0x0000000000000000000000000000000000000000')

outdir=root/'knowledge/raw/reference/polymarket_negrisk_adapter'
outdir.mkdir(parents=True,exist_ok=True)
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out=outdir/(stamp+'-anthropic-548858-e433-onchain-getters.json')
payload=dict(retrieved_at=datetime.now(timezone.utc).isoformat(),rpc=rpc,latest_block_hex=latest,adapter=adapter,market_id=market_id,adapter_code_present=True,selectors=selectors,question_count=question_count,fee_bips=fee_bips,conversion_fee_rate=fee_rate,oracle=oracle,question_count_matches_expected_10=(question_count==10),oracle_nonzero=(oracle!='0x0000000000000000000000000000000000000000'),live_trading=False,paid_actions=False,wallet_actions=False)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')
print('OUTPUT_PATH',out)
print('ANTHROPIC_NEGRISK_GETTERS_E433_PASS')
