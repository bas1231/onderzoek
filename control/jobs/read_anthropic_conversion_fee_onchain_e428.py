from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone
import json
import time

root=Path.cwd()
adapter='0xd91e80cf2e7be2e162c6513ced06f1dd0da35296'
market_id='0x4bcf7372694cb3ed70e31369f7602502cf80c6194e348bcba13c20b0a8936400'
market_prepared_topic='0xf059ab16d1ca60e123eab60e3c02b68faf060347c701a5d14885a8e1def7b3a8'
agent='PredictionEdgeHunter/1.0'

proof_dir=root/'knowledge/raw/reference/polymarket_negrisk_adapter'
proof_dir.mkdir(parents=True,exist_ok=True)

official_url='https:'+chr(47)+chr(47)+'raw.githubusercontent.com/Polymarket/agent-skills/main/README.md'
req=Request(official_url,headers={'User-Agent':agent})
with urlopen(req,timeout=30) as response:
    official_raw=response.read()
    official_status=response.status
official_text=official_raw.decode('utf-8',errors='replace')
address_verified=adapter.lower() in official_text.lower()
print('OFFICIAL_ADDRESS_SOURCE_HTTP',official_status)
print('ADAPTER_ADDRESS',adapter)
print('ADAPTER_ADDRESS_FOUND_IN_OFFICIAL_SOURCE',address_verified)
if not address_verified:
    raise SystemExit('official_adapter_address_not_verified')

source_path=proof_dir/'e428-polymarket-agent-skills-readme.txt'
source_path.write_bytes(official_raw)

endpoints=[
    'https:'+chr(47)+chr(47)+'polygon-bor-rpc.publicnode.com',
    'https:'+chr(47)+chr(47)+'polygon-rpc.com',
    'https:'+chr(47)+chr(47)+'polygon.drpc.org'
]

request_id=0
def rpc(endpoint,method,params):
    global request_id
    request_id+=1
    payload=dict(jsonrpc='2.0',id=request_id,method=method,params=params)
    body=json.dumps(payload).encode()
    req=Request(endpoint,data=body,headers={'User-Agent':agent,'Content-Type':'application/json'},method='POST')
    with urlopen(req,timeout=30) as response:
        raw=response.read()
        status=response.status
    if status!=200:
        raise RuntimeError('http_'+str(status))
    data=json.loads(raw)
    if data.get('error') is not None:
        raise RuntimeError('rpc_'+str(data.get('error'))[:500])
    return data.get('result')

chosen=None
latest=None
for endpoint in endpoints:
    try:
        value=rpc(endpoint,'eth_blockNumber',[])
        latest=int(str(value),16)
        chosen=endpoint
        print('RPC_OK',endpoint,'LATEST_BLOCK',latest)
        break
    except Exception as exc:
        print('RPC_FAILED',endpoint,str(exc)[:400])
if chosen is None or latest is None:
    raise SystemExit('no_rpc_available')

filter_base=dict(address=adapter,topics=[market_prepared_topic,market_id])
logs=None
try:
    filt=dict(filter_base)
    filt['fromBlock']='0x0'
    filt['toBlock']='latest'
    logs=rpc(chosen,'eth_getLogs',[filt])
    print('FULL_RANGE_QUERY_OK',len(logs or tuple()))
except Exception as exc:
    print('FULL_RANGE_QUERY_FAILED',str(exc)[:500])

if logs is None:
    logs=list()
    window=250000
    floor=max(0,latest-25000000)
    high=latest
    while high>=floor and not logs:
        low=max(floor,high-window+1)
        filt=dict(filter_base)
        filt['fromBlock']=hex(low)
        filt['toBlock']=hex(high)
        try:
            rows=rpc(chosen,'eth_getLogs',[filt])
            print('SCAN_RANGE',low,high,'LOGS',len(rows or tuple()))
            if rows:
                logs.extend(rows)
                break
        except Exception as exc:
            print('SCAN_RANGE_FAILED',low,high,str(exc)[:300])
        high=low-1
        time.sleep(0.05)

print('MATCHING_LOG_COUNT',len(logs or tuple()))
if not logs:
    raise SystemExit('market_prepared_log_not_found')

parsed=list()
for log in logs:
    data_hex=str(log.get('data') or '')
    clean=data_hex[2:] if data_hex.startswith('0x') else data_hex
    if len(clean)<64:
        raise SystemExit('event_data_too_short')
    fee_bips=int(clean[:64],16)
    block_number=int(str(log.get('blockNumber')),16)
    tx_hash=str(log.get('transactionHash') or '')
    topics=log.get('topics') or tuple()
    row=dict(block_number=block_number,transaction_hash=tx_hash,fee_bips=fee_bips,fee_rate=fee_bips/10000.0,topics=topics,data=data_hex)
    parsed.append(row)
    print('MARKET_PREPARED_BLOCK',block_number)
    print('MARKET_PREPARED_TX',tx_hash)
    print('FEE_BIPS',fee_bips)
    print('CONVERSION_FEE_RATE',fee_bips/10000.0)

fee_values=set(int(row.get('fee_bips')) for row in parsed)
print('UNIQUE_FEE_BIPS',sorted(fee_values))
if len(fee_values)!=1:
    raise SystemExit('ambiguous_fee_bips')
fee_bips=next(iter(fee_values))

amount=5.0
m=10
fee_amount=amount*(fee_bips/10000.0)
amount_out=amount-fee_amount
collateral_out=(m-1)*amount_out
print('EXAMPLE_AMOUNT',amount)
print('EXAMPLE_NO_COUNT',m)
print('EXAMPLE_FEE_AMOUNT_PER_UNIT',fee_amount)
print('EXAMPLE_AMOUNT_OUT',amount_out)
print('EXAMPLE_COLLATERAL_OUT_FOR_10_NO',collateral_out)

stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out=proof_dir/(stamp+'-anthropic-548858-e428-conversion-fee.json')
payload=dict(retrieved_at=datetime.now(timezone.utc).isoformat(),adapter_address=adapter,market_id=market_id,market_prepared_topic=market_prepared_topic,official_address_source=official_url,address_verified=address_verified,rpc_endpoint=chosen,matching_log_count=len(parsed),fee_bips=fee_bips,conversion_fee_rate=fee_bips/10000.0,logs=parsed,example_amount=amount,example_no_count=m,example_collateral_out=collateral_out,live_trading=False,paid_actions=False,wallet_actions=False)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')
print('OUTPUT_PATH',out)
print('ANTHROPIC_CONVERSION_FEE_ONCHAIN_E428_PASS')
