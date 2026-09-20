from urllib.request import Request,urlopen
import json

agent='PredictionEdgeHunter/1.0'
url='https:'+chr(47)+chr(47)+'gamma-api.polymarket.com/events/keyset?closed=false&limit=100'
req=Request(url,headers={'User-Agent':agent})
with urlopen(req,timeout=30) as response:
    body=response.read()
    status=response.status
print('HTTP_STATUS',status)
print('BODY_BYTES',len(body))
data=json.loads(body)
print('TOP_TYPE',type(data).name)
if isinstance(data,dict):
    print('TOP_KEYS',sorted(data.keys()))
    rows=data.get('data')
    if rows is None:
        rows=data.get('events')
    print('ROWS_TYPE',type(rows).name)
    if isinstance(rows,list):
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
    print('NEXT_CURSOR',data.get('next_cursor'))
    print('NEXT_CURSOR_ALT',data.get('nextCursor'))
elif isinstance(data,list):
    print('ROW_COUNT',len(data))
    if data:
        first=data[0]
        last=data[-1]
        if isinstance(first,dict):
            print('FIRST_ID',first.get('id'))
            print('FIRST_TITLE',first.get('title'))
        if isinstance(last,dict):
            print('LAST_ID',last.get('id'))
            print('LAST_TITLE',last.get('title'))
print('BODY_PREFIX',body[:1500].decode('utf-8',errors='replace'))
print('GAMMA_KEYSET_PROBE_PASS')
