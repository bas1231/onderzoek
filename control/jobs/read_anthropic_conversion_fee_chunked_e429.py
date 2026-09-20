from pathlib import Path
from datetime import datetime,timezone
from urllib.request import Request,urlopen
import json
import time

root=Path.cwd()
rpc_url='https:'+chr(47)+chr(47)+'polygon-bor-rpc.publicnode.com'
adapter='0xd91e80cf2e7be2e162c6513ced06f1dd0da35296'
market_id='0x4bcf7372694cb3ed70e31369f7602502cf80c6194e348bcba13c20b0a8936400'

def rpc(method,params):
    payload=json.dumps(dict(jsonrpc='2.0',id=1,method=method,params=params)).encode()
    req=Request(rpc_url,data=payload,headers={'Content-Type':'application/json','User-Agent':'PredictionEdgeHunter/1.0'},method='POST')
    with urlopen(req,timeout=30) as response:
        raw=response.read()
    data=json.loads(raw)
    if data.get('error') is not None:
        raise RuntimeError('rpc_'+str(data.get('error')))
    return data.get('result')

chain_id=int(rpc('eth_chainId',tuple()),16)
latest=int(rpc('eth_blockNumber',tuple()),16)
code=str(rpc('eth_getCode',[adapter,'latest']) or '')
print('CHAIN_ID',chain_id)
print('LATEST_BLOCK',latest)
print('ADAPTER_CODE_PRESENT',code not in ['', '0x'])
if chain_id!=137:
    raise SystemExit('unexpected_chain_id')
if code in ['', '0x']:
    raise SystemExit('adapter_code_missing')

repro_dir=root/'knowledge/raw/market_data/polymarket_reproductions'
repros=[p for p in repro_dir.iterdir() if p.is_file() and p.name.endswith('-anthropic-548858-e420.json')]
repros.sort(key=lambda p:p.stat().st_mtime)
if not repros:
    raise SystemExit('e420_missing')
repro=json.loads(repros[-1].read_text(encoding='utf-8'))
event_sha=str(repro.get('event_sha256') or '')
event_path=Path.home()/'.local/state/prediction-research/raw/polymarket_gamma_events'/(event_sha+'.json')
if not event_path.exists():
    raise SystemExit('event_raw_missing')
event=json.loads(event_path.read_text(encoding='utf-8'))

stamp_text=str(event.get('createdAt') or event.get('startDate') or '')
print('EVENT_CREATED_AT',event.get('createdAt'))
print('EVENT_START_DATE',event.get('startDate'))
print('TARGET_TIME_TEXT',stamp_text)
if not stamp_text:
    raise SystemExit('event_time_missing')
target_dt=datetime.fromisoformat(stamp_text.replace('Z','+00:00'))
target_ts=int(target_dt.timestamp())
print('TARGET_UNIX',target_ts)

low=max(0,latest-10000000)
high=latest
best=None
for step in range(40):
    if low>high:
        break
    mid=(low+high)//2
    block=rpc('eth_getBlockByNumber',[hex(mid),False])
    if not isinstance(block,dict):
        raise SystemExit('block_lookup_failed_'+str(mid))
    ts=int(str(block.get('timestamp')),16)
    best=(mid,ts)
    if ts<target_ts:
        low=mid+1
    elif ts>target_ts:
        high=mid-1
    else:
        break

candidate_blocks=[value for value in [low,high,(best[0] if best else None)] if isinstance(value,int) and value>=0 and value<=latest]
nearest=None
nearest_delta=None
for number in sorted(set(candidate_blocks)):
    block=rpc('eth_getBlockByNumber',[hex(number),False])
    if not isinstance(block,dict):
        continue
    ts=int(str(block.get('timestamp')),16)
    delta=abs(ts-target_ts)
    if nearest is None or delta<nearest_delta:
        nearest=number
        nearest_delta=delta
print('NEAREST_BLOCK',nearest)
print('NEAREST_TIME_DELTA_SECONDS',nearest_delta)
if nearest is None:
    raise SystemExit('nearest_block_missing')

signature='MarketPrepared(bytes32,address,uint256,bytes)'
sig_hex='0x'+signature.encode().hex()
topic0=None
try:
    topic0=rpc('web3_sha3',[sig_hex])
except Exception as exc:
    print('WEB3_SHA3_UNAVAILABLE',str(exc)[:300])
print('MARKET_PREPARED_TOPIC0',topic0)

radius=500000
chunk=9000
scan_start=max(0,nearest-radius)
scan_end=min(latest,nearest+radius)
print('SCAN_START',scan_start)
print('SCAN_END',scan_end)
print('SCAN_RADIUS',radius)
print('CHUNK_SIZE',chunk)

logs=list()
current=scan_start
queries=0
while current<=scan_end:
    end=min(scan_end,current+chunk-1)
    topics=[topic0,market_id] if topic0 else [None,market_id]
    params=dict(address=adapter,fromBlock=hex(current),toBlock=hex(end),topics=topics)
    result=None
    for attempt in [1,2,3]:
        try:
            result=rpc('eth_getLogs',[params])
            break
        except Exception as exc:
            print('RANGE_RETRY',current,end,attempt,str(exc)[:300])
            if attempt<3:
                time.sleep(1)
    if result is None:
        raise SystemExit('range_failed_'+str(current)+'_'+str(end))
    queries+=1
    if result:
        print('RANGE_MATCH',current,end,'COUNT',len(result))
        for item in result:
            if isinstance(item,dict):
                logs.append(item)
    current=end+1

print('LOG_QUERY_COUNT',queries)
print('MATCHING_LOG_COUNT',len(logs))

parsed=list()
for item in logs:
    topics=item.get('topics') or tuple()
    data=str(item.get('data') or '')
    block_number=int(str(item.get('blockNumber') or '0x0'),16)
    tx_hash=str(item.get('transactionHash') or '')
    event_topic=str(topics[0]) if topics else ''
    indexed_market=str(topics[1]) if len(topics)>1 else ''
    oracle_topic=str(topics[2]) if len(topics)>2 else ''
    fee_bips=None
    if data.startswith('0x') and len(data)>=66:
        fee_bips=int(data[2:66],16)
    row=dict(block_number=block_number,transaction_hash=tx_hash,event_topic=event_topic,indexed_market_id=indexed_market,oracle_topic=oracle_topic,fee_bips=fee_bips,data=data)
    parsed.append(row)
    print('LOG','BLOCK',block_number,'TX',tx_hash,'TOPIC0',event_topic,'MARKET_TOPIC',indexed_market,'ORACLE_TOPIC',oracle_topic,'FEE_BIPS',fee_bips)

exact=[row for row in parsed if str(row.get('indexed_market_id')).lower()==market_id.lower()]
plausible=[row for row in exact if row.get('fee_bips') is not None and int(row.get('fee_bips'))>=0 and int(row.get('fee_bips'))<=10000]
print('EXACT_MARKET_LOG_COUNT',len(exact))
print('PLAUSIBLE_FEE_LOG_COUNT',len(plausible))
for row in plausible:
    print('CONVERSION_FEE_BIPS',row.get('fee_bips'))
    print('CONVERSION_FEE_RATE',float(row.get('fee_bips'))/10000.0)

outdir=root/'knowledge/raw/reference/polymarket_negrisk_adapter'
outdir.mkdir(parents=True,exist_ok=True)
out=outdir/'e429-anthropic-548858-marketprepared-onchain.json'
payload=dict(retrieved_at=datetime.now(timezone.utc).isoformat(),rpc_url=rpc_url,chain_id=chain_id,adapter_address=adapter,market_id=market_id,event_time=stamp_text,target_unix=target_ts,nearest_block=nearest,nearest_time_delta_seconds=nearest_delta,scan_start=scan_start,scan_end=scan_end,chunk_size=chunk,query_count=queries,market_prepared_topic0=topic0,matching_logs=parsed,plausible_fee_logs=plausible,live_trading=False,paid_actions=False,wallet_actions=False)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')
print('OUTPUT_PATH',out)
if not plausible:
    raise SystemExit('market_prepared_log_not_found_in_bounded_window')
print('ANTHROPIC_CONVERSION_FEE_ONCHAIN_E429_PASS')
