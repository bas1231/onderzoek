from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlencode
import json
import hashlib

raw_dir=Path.home()/'.local/state/prediction-research/raw/polymarket_gamma_keyset'
files=[p for p in raw_dir.iterdir() if p.is_file() and p.suffix=='.json']
if not files:
    raise SystemExit('raw_keyset_missing')

first_path=None
first=None
for p in files:
    try:
        data=json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        continue
    rows=data.get('events') or tuple()
    if isinstance(rows,list) and len(rows)==100 and str(data.get('next_cursor') or ''):
        first_path=p
        first=data
        break
if first is None:
    raise SystemExit('usable_first_page_missing')

rows1=first.get('events') or tuple()
first_first=str((rows1[0] or dict()).get('id') or '')
first_last=str((rows1[-1] or dict()).get('id') or '')
cursor=str(first.get('next_cursor') or '')

base='https:'+chr(47)+chr(47)+'gamma-api.polymarket.com/events/keyset'
params=dict(active='true',closed='false',limit='100',after_cursor=cursor)
url=base+'?'+urlencode(params)
req=Request(url,headers={'User-Agent':'PredictionEdgeHunter/1.0'})
with urlopen(req,timeout=40) as response:
    body=response.read()
    status=response.status
second=json.loads(body)
rows2=second.get('events') or tuple()
if not isinstance(rows2,list):
    raise SystemExit('second_page_shape_bad')
second_first=str((rows2[0] or dict()).get('id') or '') if rows2 else ''
second_last=str((rows2[-1] or dict()).get('id') or '') if rows2 else ''
next_cursor=str(second.get('next_cursor') or '')
sha=hashlib.sha256(body).hexdigest()
out=raw_dir/(sha+'.json')
if not out.exists():
    out.write_bytes(body)

advanced=bool(rows2 and (second_first!=first_first or second_last!=first_last))
cursor_changed=bool(next_cursor and next_cursor!=cursor)
unique1=set(str((row or dict()).get('id') or '') for row in rows1 if isinstance(row,dict))
unique2=set(str((row or dict()).get('id') or '') for row in rows2 if isinstance(row,dict))
overlap=len(unique1.intersection(unique2))

print('FIRST_RAW',first_path)
print('FIRST_FIRST_ID',first_first)
print('FIRST_LAST_ID',first_last)
print('FIRST_CURSOR_LENGTH',len(cursor))
print('HTTP_STATUS',status)
print('SECOND_ROW_COUNT',len(rows2))
print('SECOND_FIRST_ID',second_first)
print('SECOND_LAST_ID',second_last)
print('SECOND_SHA256',sha)
print('SECOND_RAW',out)
print('NEXT_CURSOR_LENGTH',len(next_cursor))
print('CURSOR_CHANGED',cursor_changed)
print('PAGE_ID_OVERLAP',overlap)
print('PAGE_ADVANCED',advanced)
if not advanced:
    raise SystemExit('after_cursor_did_not_advance')
if not cursor_changed:
    raise SystemExit('next_cursor_did_not_change')
print('GAMMA_AFTER_CURSOR_VERIFY_PASS')
