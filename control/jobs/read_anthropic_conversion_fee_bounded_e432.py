from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone
import json
import time

root=Path.cwd()
rpc='https:'+chr(47)+chr(47)+'polygon-bor-rpc.publicnode.com'
adapter='0xd91e80cf2e7be2e162c6513ced06f1dd0da35296'
market_id='0x4bcf7372694cb3ed70e31369f7602502cf80c6194e348bcba13c20b0a8936400'

repro_dir=root/'knowledge/raw/market_data/polymarket_reproductions'
files=[p for p in repro_dir.iterdir() if p.is_file() and p.name.endswith('-anthropic-548858-e420.json')]
files.sort(key=lambda p:p.stat().st_mtime)
if not files:
    raise SystemExit('e420_missing')
repro=json.loads(files[-1].read_text(encoding='utf-8'))
event_sha=str(repro.get('event_sha256') or '')
event_path=Path.home()/'.local/state/prediction-research/raw/polymarket_gamma_events'/(event_sha+'.json')
if not event_path.exists():
    raise SystemExit('event_raw_missing')
event=json.loads(event_path.read_text(encoding='utf-8'))
start_text=str(event.get('startDate') or '')
if not start_text:
    raise SystemExit('event_start_missing')
start_dt=datetime.fromisoformat(start_text.replace('Z','+00:00'))
target_ts=int(start_dt.timestamp())

counter=0
def rpc_call(method,params):
    global counter
    counter+=1
    payload=json.dumps(dict(jsonrpc='2.0',id=counter,method=method,params=params)).encode()
    req=Request(rpc,data=payload,headers={'User-Agent':'PredictionEdgeHunter/1.0','Content-Type':'application/json'},method='POST')
    with urlopen(req,timeout=30) as response:
        raw=response.read()
        status=response.status
    if status!=200:
        raise RuntimeError('http_'+str(status))
    data=json.loads(raw)
    if data.get('error') is not None:
        raise RuntimeError('rpc_'+str(data.get('error')))
    return data.get('result')

latest_hex=rpc_call('eth_blockNumber',[])
latest=int(latest_hex,16)
print('LATEST_BLOCK',latest)
print('EVENT_START',start_text)
print('EVENT_START_TS',target_ts)
print('ADAPTER',adapter)
print('MARKET_ID',market_id)

signature='MarketPrepared(bytes32,address,uint256,bytes)'
sig_hex='0x'+signature.encode().hex()
topic0=rpc_call('web3_sha3',[sig_hex])
if not isinstance(topic0,str) or not topic0.startswith('0x'):
    raise SystemExit('topic_hash_failed')
print('TOPIC0',topic0)

low=max(70000000,latest-30000000)
high=latest
closest=None
while low<=high:
    mid=(low+high)//2
    try:
        block=rpc_call('eth_getBlockByNumber',[hex(mid),False])
    except Exception:
        low=mid+1
        continue
    if not isinstance(block,dict):
        low=mid+1
        continue
    ts=int(str(block.get('timestamp')),16)
    closest=(mid,ts)
    if ts<target_ts:
        low=mid+1
    elif ts>target_ts:
        high=mid-1
    else:
        break

if closest is None:
    raise SystemExit('target_block_not_found')
center=closest[0]
print('CENTER_BLOCK',center)
print('CENTER_TS',closest[1])
print('CENTER_TIME',datetime.fromtimestamp(closest[1],timezone.utc).isoformat())

windows=[100000,500000]
found=list()
queries=0
for radius in windows:
    start=max(0,center-radius)
    end=min(latest,center+radius)
    cursor=start
    while cursor<=end:
        to_block=min(end,cursor+9999)
        params=[dict(address=adapter,fromBlock=hex(cursor),toBlock=hex(to_block),topics=[topic0,market_id])]
        try:
            logs=rpc_call('eth_getLogs',params)
        except Exception as exc:
            print('LOG_RANGE_FAILED',cursor,to_block,str(exc)[:400])
            cursor=to_block+1
            continue
        queries+=1
        if isinstance(logs,list) and logs:
            for log in logs:
                if isinstance(log,dict):
                    found.append(log)
            break
        cursor=to_block+1
    if found:
        print('FOUND_WITH_RADIUS',radius)
        break

print('LOG_QUERY_COUNT',queries)
print('MATCHING_LOG_COUNT',len(found))
rows=list()
for log in found:
    data_hex=str(log.get('data') or '')
    body=data_hex[2:] if data_hex.startswith('0x') else data_hex
    if len(body)<64:
        print('BAD_LOG_DATA',data_hex)
        continue
    fee_bips=int(body[:64],16)
    block_number=int(str(log.get('blockNumber')),16)
    tx_hash=str(log.get('transactionHash') or '')
    fee_fraction=fee_bips/10000.0
    row=dict(block_number=block_number,transaction_hash=tx_hash,fee_bips=fee_bips,fee_fraction=fee_fraction,data=data_hex,topics=log.get('topics'))
    rows.append(row)
    print('MARKET_PREPARED_BLOCK',block_number)
    print('MARKET_PREPARED_TX',tx_hash)
    print('CONVERSION_FEE_BIPS',fee_bips)
    print('CONVERSION_FEE_FRACTION',fee_fraction)

if not rows:
    raise SystemExit('market_prepared_log_not_found_in_bounded_window')

unique_fees=sorted(set(int(row.get('fee_bips')) for row in rows))
print('UNIQUE_FEE_BIPS',unique_fees)
if len(unique_fees)!=1:
    raise SystemExit('ambiguous_fee_bips')

outdir=root/'knowledge/raw/reference/polymarket_negrisk_adapter'
outdir.mkdir(parents=True,exist_ok=True)
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out=outdir/(stamp+'-anthropic-548858-e432-conversion-fee.json')
payload=dict(retrieved_at=datetime.now(timezone.utc).isoformat(),rpc=rpc,adapter_address=adapter,market_id=market_id,event_start=start_text,center_block=center,topic0=topic0,matching_log_count=len(rows),fee_bips=unique_fees[0],fee_fraction=unique_fees[0]/10000.0,logs=rows,live_trading=False,paid_actions=False,wallet_actions=False)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')
print('OUTPUT_PATH',out)
print('ANTHROPIC_CONVERSION_FEE_BOUNDED_E432_PASS')
