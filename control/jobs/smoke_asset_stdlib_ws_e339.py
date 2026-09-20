from pathlib import Path
from datetime import datetime,timezone
import base64
import json
import os
import socket
import ssl
import time

root=Path.cwd()
source=root/'knowledge/raw/market_data/polymarket_neg_risk_partial/20260920T013900Z106981.json'
if not source.exists():
    raise SystemExit('source_snapshot_missing')
data=json.loads(source.read_text(encoding='utf-8'))
markets=data.get('markets') or tuple()
if len(markets)!=3:
    raise SystemExit('market_count_wrong')
assets=list()
for market in markets:
    token=str(market.get('yes_token') or '')
    if not token:
        raise SystemExit('token_missing')
    assets.append(token)

host='ws-subscriptions-clob.polymarket.com'
path='/ws/market'

def recv_exact(sock,count):
    chunks=list()
    have=0
    while have<count:
        part=sock.recv(count-have)
        if not part:
            raise ConnectionError('socket_closed')
        chunks.append(part)
        have+=len(part)
    return b''.join(chunks)

def send_frame(sock,opcode,payload):
    if isinstance(payload,str):
        payload=payload.encode('utf-8')
    size=len(payload)
    first=0x80+opcode
    if size<126:
        header=bytes((first,0x80+size))
    elif size<65536:
        header=bytes((first,0x80+126))+size.to_bytes(2,'big')
    else:
        header=bytes((first,0x80+127))+size.to_bytes(8,'big')
    mask=os.urandom(4)
    masked=bytes(value ^ mask[index % 4] for index,value in enumerate(payload))
    sock.sendall(header+mask+masked)

def recv_frame(sock):
    head=recv_exact(sock,2)
    first=head[0]
    second=head[1]
    opcode=first & 15
    masked=(second & 128)!=0
    size=second & 127
    if size==126:
        size=int.from_bytes(recv_exact(sock,2),'big')
    elif size==127:
        size=int.from_bytes(recv_exact(sock,8),'big')
    mask=None
    if masked:
        mask=recv_exact(sock,4)
    payload=recv_exact(sock,size) if size else b''
    if masked and mask is not None:
        payload=bytes(value ^ mask[index % 4] for index,value in enumerate(payload))
    return opcode,payload

raw_sock=socket.create_connection((host,443),timeout=10)
ctx=ssl.create_default_context()
sock=ctx.wrap_socket(raw_sock,server_hostname=host)
sock.settimeout(1.0)
key=base64.b64encode(os.urandom(16)).decode('ascii')
request='GET '+path+' HTTP/1.1
Host: '+host+'
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: '+key+'
Sec-WebSocket-Version: 13
User-Agent: PredictionEdgeHunter/1.0

'
sock.sendall(request.encode('ascii'))
header=b''
while b'

' not in header:
    part=sock.recv(4096)
    if not part:
        raise SystemExit('handshake_closed')
    header+=part
    if len(header)>65536:
        raise SystemExit('handshake_too_large')
text=header.decode('latin1',errors='replace')
status_line=text.split('
',1)[0]
print('HANDSHAKE_STATUS',status_line)
if ' 101 ' not in status_line:
    print(text[:4000])
    raise SystemExit('websocket_handshake_failed')

subscription=dict(assets_ids=assets,type='market',custom_feature_enabled=True)
send_frame(sock,1,json.dumps(subscription))

stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
outdir=root/'knowledge/raw/market_data/polymarket_shadow_smoke'
outdir.mkdir(parents=True,exist_ok=True)
out=outdir/(stamp+'106981.jsonl')
counts=dict()
frames=0
pings_sent=0
pongs_seen=0
start=time.monotonic()
last_ping=start

with out.open('a',encoding='utf-8') as fh:
    while time.monotonic()-start<45:
        now=time.monotonic()
        if now-last_ping>=10:
            send_frame(sock,1,'PING')
            pings_sent+=1
            last_ping=now
        try:
            opcode,payload=recv_frame(sock)
        except socket.timeout:
            continue
        received=datetime.now(timezone.utc).isoformat()
        if opcode==9:
            send_frame(sock,10,payload)
            fh.write(json.dumps(dict(received_at=received,opcode=opcode,raw=base64.b64encode(payload).decode('ascii')))+chr(10))
            fh.flush()
            continue
        if opcode==10:
            pongs_seen+=1
            fh.write(json.dumps(dict(received_at=received,opcode=opcode,raw='PONG'))+chr(10))
            fh.flush()
            continue
        if opcode==8:
            fh.write(json.dumps(dict(received_at=received,opcode=opcode,raw=base64.b64encode(payload).decode('ascii')))+chr(10))
            fh.flush()
            break
        if opcode!=1:
            fh.write(json.dumps(dict(received_at=received,opcode=opcode,raw=base64.b64encode(payload).decode('ascii')))+chr(10))
            fh.flush()
            continue
        message=payload.decode('utf-8',errors='replace')
        frames+=1
        fh.write(json.dumps(dict(received_at=received,opcode=opcode,raw=message))+chr(10))
        fh.flush()
        try:
            parsed=json.loads(message)
        except Exception:
            counts['NON_JSON']=counts.get('NON_JSON',0)+1
            continue
        items=parsed if isinstance(parsed,list) else [parsed]
        for item in items:
            if isinstance(item,dict):
                keyname=str(item.get('event_type') or item.get('type') or 'UNKNOWN')
            else:
                keyname='NON_OBJECT'
            counts[keyname]=counts.get(keyname,0)+1

try:
    send_frame(sock,8,b'')
except Exception:
    pass
try:
    sock.close()
except Exception:
    pass

print('TEXT_FRAMES',frames)
print('PING_TEXT_SENT',pings_sent)
print('PONG_FRAMES_SEEN',pongs_seen)
for keyname in sorted(counts):
    print('EVENT_COUNT',keyname,counts.get(keyname))
print('PATH',out)
print('AFTER_PREREG',datetime.now(timezone.utc).isoformat())
if frames<=0:
    raise SystemExit('no_market_frames_received')
print('ASSET_STDLIB_WS_SMOKE_PASS')
