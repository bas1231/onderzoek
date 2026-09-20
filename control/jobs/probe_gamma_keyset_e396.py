from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone
import hashlib
import json

agent='PredictionEdgeHunter/1.0'
url='https:'+chr(47)+chr(47)+'gamma-api.polymarket.com/events/keyset?active=true&closed=false&limit=100'
req=Request(url,headers={'User-Agent':agent})
with urlopen(req,timeout=30) as response:
    body=response.read()
    status=response.status

sha=hashlib.sha256(body).hexdigest()
state=Path.home()/'.local/state/prediction-research/raw/polymarket_gamma_keyset'
state.mkdir(parents=True,exist_ok=True)
raw_path=state/(sha+'.json')
if not raw_path.exists():
    raw_path.write_bytes(body)

data=json.loads(body)
print('HTTP_STATUS',status)
print('BODY_BYTES',len(body))
print('SHA256',sha)
print('RAW_PATH',raw_path)

if isinstance(data,dict):
    print('TOP_KIND','dict')
    print('TOP_KEYS',sorted(data.keys()))
    rows=data.get('data')
    if rows is None:
        rows=data.get('events')
    if isinstance(rows,list):
        print('ROWS_KIND','list')
        print('ROW_COUNT',len(rows))
        if rows:
            first=rows[0]
            last=rows[-1]
            if isinstance(first,dict):
                print('FIRST_KEYS',sorted(first.keys()))
                print('FIRST_ID',first.get('id'))
                print('FIRST_TITLE',first.get('title'))
                print('FIRST_ACTIVE',first.get('active'))
                print('FIRST_CLOSED',first.get('closed'))
            if isinstance(last,dict):
                print('LAST_ID',last.get('id'))
                print('LAST_TITLE',last.get('title'))
                print('LAST_ACTIVE',last.get('active'))
                print('LAST_CLOSED',last.get('closed'))
    else:
        print('ROWS_KIND','other')
    print('NEXT_CURSOR',data.get('next_cursor'))
    print('NEXT_CURSOR_ALT',data.get('nextCursor'))
elif isinstance(data,list):
    print('TOP_KIND','list')
    print('ROW_COUNT',len(data))
    if data:
        first=data[0]
        last=data[-1]
        if isinstance(first,dict):
            print('FIRST_ID',first.get('id'))
            print('FIRST_TITLE',first.get('title'))
            print('FIRST_ACTIVE',first.get('active'))
            print('FIRST_CLOSED',first.get('closed'))
        if isinstance(last,dict):
            print('LAST_ID',last.get('id'))
            print('LAST_TITLE',last.get('title'))
            print('LAST_ACTIVE',last.get('active'))
            print('LAST_CLOSED',last.get('closed'))
else:
    print('TOP_KIND','other')

print('GAMMA_KEYSET_PROBE_E396_PASS')
