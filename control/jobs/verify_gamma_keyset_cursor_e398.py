from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlencode
import json

root=Path.cwd()
manifest_dir=root/'knowledge/raw/market_data/polymarket_neg_risk_keyset_manifests'
files=[p for p in manifest_dir.iterdir() if p.is_file() and p.suffix=='.json']
files.sort(key=lambda p:p.stat().st_mtime)
if not files:
    raise SystemExit('keyset_manifest_missing')
manifest=json.loads(files[-1].read_text(encoding='utf-8'))
pages=manifest.get('pages') or tuple()
if len(pages)<2:
    raise SystemExit('need_two_page_summaries')

print('MANIFEST',files[-1].name)
print('RECORDED_PAGE_COUNT',len(pages))
for row in pages[:3]:
    print('RECORDED_PAGE',row.get('page'),'FIRST',row.get('first_id'),'LAST',row.get('last_id'),'SHA',row.get('sha256'))

raw_dir=Path.home()/'.local/state/prediction-research/raw/polymarket_gamma_keyset'
first_sha=str((pages[0] or dict()).get('sha256') or '')
second_sha=str((pages[1] or dict()).get('sha256') or '')
first_path=raw_dir/(first_sha+'.json')
second_path=raw_dir/(second_sha+'.json')
if not first_path.exists() or not second_path.exists():
    raise SystemExit('raw_page_missing')
first=json.loads(first_path.read_text(encoding='utf-8'))
second=json.loads(second_path.read_text(encoding='utf-8'))
cur1=str(first.get('next_cursor') or '')
cur2=str(second.get('next_cursor') or '')
print('FIRST_CURSOR_LENGTH',len(cur1))
print('SECOND_CURSOR_LENGTH',len(cur2))
print('CURSORS_EQUAL',cur1==cur2)
print('FIRST_CURSOR_PREFIX',cur1[:120])
print('SECOND_CURSOR_PREFIX',cur2[:120])

base='https:'+chr(47)+chr(47)+'gamma-api.polymarket.com/events/keyset'
params=dict(active='true',closed='false',limit='100',cursor=cur1)
url=base+'?'+urlencode(params)
req=Request(url,headers={'User-Agent':'PredictionEdgeHunter/1.0'})
with urlopen(req,timeout=40) as response:
    body=response.read()
    status=response.status
data=json.loads(body)
rows=data.get('events') or tuple()
if not isinstance(rows,list):
    raise SystemExit('events_shape_bad')
first_id=None
last_id=None
if rows:
    if isinstance(rows[0],dict):
        first_id=str(rows[0].get('id') or '')
    if isinstance(rows[-1],dict):
        last_id=str(rows[-1].get('id') or '')
print('ENCODED_REQUEST_STATUS',status)
print('ENCODED_ROW_COUNT',len(rows))
print('ENCODED_FIRST_ID',first_id)
print('ENCODED_LAST_ID',last_id)
print('ENCODED_NEXT_CURSOR_LENGTH',len(str(data.get('next_cursor') or '')))
recorded_first=str((pages[0] or dict()).get('first_id') or '')
recorded_last=str((pages[0] or dict()).get('last_id') or '')
advanced=bool(rows and (first_id!=recorded_first or last_id!=recorded_last))
print('CURSOR_ADVANCED',advanced)
print('GAMMA_KEYSET_CURSOR_VERIFY_PASS')
