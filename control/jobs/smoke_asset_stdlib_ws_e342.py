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
crlf=chr(13)+chr(10)
header_end=bytes((13,10,13,10))

def recv_exact(sock,count):
    parts=list()
    have=0
    while have<count:
        part=sock.recv(count-have)
        if not part:
            raise ConnectionError('socket_closed')
        parts.append(part)
        have+=len(part)
    return b''.join(parts)

def send_frame(sock,opcode,payload):
    if isinstance(payload,str):
        payload=payload.encode('utf-8')
    size=len(payload)
    first=128+opcode
    if size<126:
        header=bytes((first,128+size))
    elif size<65536:
        header=bytes((first,254))+size.to_bytes(2,'big')
    else:
        header=bytes((first,255))+size.to_bytes(8,'big')
    mask=os.urandom(4)
    out=bytearray()
    for index,value in enumerate(payload):
        out.append(value ^ mask[index % 4])
    sock.sendall(header+mask+bytes(out))

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
    if masked:
        raise ConnectionError('server_frame_masked')
    payload=recv_exact(sock,size) if size else b''
    return opcode,payload

raw_sock=socket.create_connection((host,443),timeout=10)
ctx=ssl.create_default_context()
sock=ctx.wrap_socket(raw_sock,server_hostname=host)
sock.settimeout(1.0)
key=base64.b64encode(os.urandom(16)).decode('ascii')
request_lines=list()
request_lines.append('GET '+path+' HTTP/1.1')
request_lines.append('Host: '+host)
request_lines.append('Upgrade: websocket')
request_lines.append('Connection: Upgrade')
request_lines.append('Sec-WebSocket-Key: '+key)
request_lines.append('Sec-WebSocket-Version: 13')
request_lines.append('User-Agent: PredictionEdgeHunter/1.0')
request_lines.append('')
request_lines.append('')
request=crlf.join(request_lines)
sock.sendall(request.encode('ascii'))
header=b''
while header_end not in header:
    part=sock.recv(4096)
    if not part:
        raise SystemExit('handshake_closed')
    header+=part
    if len(header)>65536:
        raise SystemExit('handshake_too_large')
text=header.decode('latin1',errors='replace')
status_line=next(iter(text.split(crlf,1)),'')
print('HANDSHAKE_STATUS',status_line)
if ' 101 ' not in status_line:
    raise SystemExit('websocket_handshake_failed')

subscription=dict(assets_ids=assets,type='market',custom_feature_enabled=True)
send_frame(sock,1,json.dumps(subscription))

stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
outdir=root/'knowledge/raw/market_data/polymarket_shadow_smoke'
outdir.mkdir(parents=True,exist_ok=True)
out=outdir/(stamp+'106981.jsonl')
counts=dict()
text_frames=0
pong_text=0
start=time.monotonic()
last_ping=start

with out.open('a',encoding='utf-8') as fh:
    while time.monotonic()-start<45:
        now=time.monotonic()
        if now-last_ping>=10:
            send_frame(sock,1,'PING')
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
        if opcode==8:
            fh.write(json.dumps(dict(received_at=received,opcode=opcode,raw=base64.b64encode(payload).decode('ascii')))+chr(10))
            fh.flush()
            break
        if opcode!=1:
            fh.write(json.dumps(dict(received_at=received,opcode=opcode,raw=base64.b64encode(payload).decode('ascii')))+chr(10))
            fh.flush()
            continue
        message=payload.decode('utf-8',errors='replace')
        text_frames+=1
        fh.write(json.dumps(dict(received_at=received,opcode=opcode,raw=message))+chr(10))
        fh.flush()
        if message=='PONG':
            pong_text+=1
            continue
        try:
            parsed=json.loads(message)
        except Exception:
            counts['NON_JSON']=counts.get('NON_JSON',0)+1
            continue
        items=parsed if isinstance(parsed,list) else [parsed]
        for item in items:
            if isinstance(item,dict):
                kind=str(item.get('event_type') or item.get('type') or 'UNKNOWN')
            else:
                kind='NON_OBJECT'
            counts[kind]=counts.get(kind,0)+1

try:
    send_frame(sock,8,b'')
except Exception:
    pass
try:
    sock.close()
except Exception:
    pass

print('TEXT_FRAMES',text_frames)
print('PONG_TEXT',pong_text)
for kind in sorted(counts):
    print('EVENT_COUNT',kind,counts.get(kind))
print('PATH',out)
print('AFTER_PREREG',datetime.now(timezone.utc).isoformat())
if text_frames<=0:
    raise SystemExit('no_market_frames_received')
print('ASSET_STDLIB_WS_SMOKE_PASS')
