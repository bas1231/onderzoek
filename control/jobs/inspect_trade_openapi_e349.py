from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from datetime import datetime,timezone
import json

root=Path.cwd()
urls=[
    'https:'+chr(47)+chr(47)+'data-api.polymarket.com/v2/openapi.json',
    'https:'+chr(47)+chr(47)+'data-api.polymarket.com/openapi.json',
    'https:'+chr(47)+chr(47)+'data-api.polymarket.com/v2/docs'
]

found=None
raw=None
for url in urls:
    try:
        req=Request(url,headers={'User-Agent':'PredictionEdgeHunter/1.0','Accept':'application/json,text/html'})
        with urlopen(req,timeout=30) as r:
            body=r.read()
            print('URL',url)
            print('HTTP',r.status)
            print('CONTENT_TYPE',r.headers.get('Content-Type'))
            print('BYTES',len(body))
            try:
                data=json.loads(body)
            except Exception:
                data=None
            if isinstance(data,dict) and data.get('openapi'):
                found=url
                raw=body
                break
    except HTTPError as exc:
        print('URL',url)
        print('HTTP_ERROR',exc.code)
    except URLError as exc:
        print('URL',url)
        print('URL_ERROR',str(exc.reason)[:500])

if raw is None:
    raise SystemExit('openapi_not_found')

data=json.loads(raw)
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
outdir=root/'knowledge/raw/platform_docs/polymarket'
outdir.mkdir(parents=True,exist_ok=True)
out=outdir/(stamp+'data_api_openapi.json')
out.write_bytes(raw)

print('OPENAPI_URL',found)
print('OPENAPI_VERSION',data.get('openapi'))
paths=data.get('paths') or dict()
trade_path=paths.get('/v2/trades') or dict()
getop=trade_path.get('get') or dict()
print('TRADE_OPERATION_SUMMARY',getop.get('summary'))
print('TRADE_OPERATION_DESCRIPTION',str(getop.get('description') or '')[:6000])
for param in getop.get('parameters') or tuple():
    if not isinstance(param,dict):
        continue
    name=str(param.get('name') or '')
    if name.lower() in ['side','takeronly','taker_only','event_id','condition']:
        print('PARAM',name)
        print('PARAM_DESCRIPTION',str(param.get('description') or '')[:4000])
        print('PARAM_SCHEMA',json.dumps(param.get('schema') or dict(),sort_keys=True)[:4000])

responses=getop.get('responses') or dict()
ok=responses.get('200') or dict()
print('RESPONSE_200',json.dumps(ok,sort_keys=True)[:12000])

schemas=((data.get('components') or dict()).get('schemas') or dict())
for name,schema in schemas.items():
    low=str(name).lower()
    text=json.dumps(schema,sort_keys=True)
    text_low=text.lower()
    if 'trade' in low or ('token_id' in text_low and 'side' in text_low):
        print('SCHEMA_NAME',name)
        print('SCHEMA_BODY',text[:16000])

print('PATH',out)
print('TRADE_OPENAPI_INSPECTION_PASS')
