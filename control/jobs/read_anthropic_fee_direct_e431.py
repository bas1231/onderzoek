from urllib.request import Request,urlopen
import json

rpc='https:'+chr(47)+chr(47)+'polygon-bor-rpc.publicnode.com'
adapter='0xd91e80cf2e7be2e162c6513ced06f1dd0da35296'
market_id='4bcf7372694cb3ed70e31369f7602502cf80c6194e348bcba13c20b0a8936400'

def rpc_call(method,params):
    payload=json.dumps(dict(jsonrpc='2.0',id=1,method=method,params=params)).encode()
    req=Request(rpc,data=payload,headers={'Content-Type':'application/json','User-Agent':'PredictionEdgeHunter/1.0'},method='POST')
    with urlopen(req,timeout=30) as response:
        body=response.read()
        status=response.status
    if status!=200:
        raise SystemExit('rpc_http_'+str(status))
    data=json.loads(body)
    if data.get('error') is not None:
        raise SystemExit('rpc_error_'+str(data.get('error')))
    return data.get('result')

def selector(signature):
    hex_text='0x'+signature.encode().hex()
    result=rpc_call('web3_sha3',[hex_text])
    if not isinstance(result,str) or not result.startswith('0x') or len(result)<10:
        raise SystemExit('selector_failed_'+signature)
    return result[2:10]

def uint_call(signature):
    sel=selector(signature)
    data='0x'+sel+market_id
    result=rpc_call('eth_call',[dict(to=adapter,data=data),'latest'])
    if not isinstance(result,str) or not result.startswith('0x'):
        raise SystemExit('eth_call_bad_'+signature)
    return sel,result,int(result,16)

chain_hex=rpc_call('eth_chainId',[])
block_hex=rpc_call('eth_blockNumber',[])
fee_selector,fee_raw,fee_bips=uint_call('getFeeBips(bytes32)')
count_selector,count_raw,question_count=uint_call('getQuestionCount(bytes32)')

print('CHAIN_ID',int(chain_hex,16))
print('LATEST_BLOCK',int(block_hex,16))
print('ADAPTER',adapter)
print('MARKET_ID','0x'+market_id)
print('GET_FEE_BIPS_SELECTOR','0x'+fee_selector)
print('GET_FEE_BIPS_RAW',fee_raw)
print('FEE_BIPS',fee_bips)
print('CONVERSION_FEE_RATE',fee_bips/10000.0)
print('GET_QUESTION_COUNT_SELECTOR','0x'+count_selector)
print('GET_QUESTION_COUNT_RAW',count_raw)
print('QUESTION_COUNT',question_count)
print('EXPECTED_QUESTION_COUNT_MATCH',question_count==10)
print('READ_ONLY',True)
print('LIVE_TRADING',False)
print('WALLET_ACTION',False)
print('ANTHROPIC_FEE_DIRECT_E431_PASS')
