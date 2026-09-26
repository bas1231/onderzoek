"""Vaste publieke GET-capability; geen headers/auth/body van researchcode accepteren."""
import os,stat,tempfile
import base64,hashlib,json,datetime,re,urllib.parse,urllib.request
from pathlib import Path
DOC_URLS=frozenset(['https://docs.kalshi.com/','https://docs.polymarket.com/','https://www.cftc.gov/','https://aviationweather.gov/','https://www.weather.gov/','https://www.ecmwf.int/en/forecasts/datasets/open-data','https://nomads.ncep.noaa.gov/','https://arxiv.org/','https://github.com/','https://www.reddit.com/','https://www.youtube.com/','https://help.kalshi.com/en/articles/13823837-weather-markets','https://weather.com/kalshi'])
def allowed(url):
    if url in DOC_URLS:return True
    p=urllib.parse.urlsplit(url)
    if p.scheme=='https' and p.netloc=='data-api.polymarket.com' and p.path=='/v2/trades' and not p.fragment:
        q=urllib.parse.parse_qs(p.query,strict_parsing=True)
        return (not set(q)-{'event_id','limit','taker_only','cursor'} and all(len(v)==1 for v in q.values()) and q.get('event_id')==['106981'] and q.get('limit')==['100'] and q.get('taker_only')==['true'] and ('cursor' not in q or len(q['cursor'][0])<=1024))
    if p.scheme!='https' or p.netloc!='external-api.kalshi.com' or p.path not in ('/trade-api/v2/markets','/trade-api/v2/events') or p.fragment:return False
    q=urllib.parse.parse_qs(p.query,strict_parsing=True)
    if set(q)-{'limit','status','with_nested_markets','cursor'} or any(len(v)!=1 for v in q.values()):return False
    if q.get('status')!=['open'] or q.get('limit') not in (['200'],['1000']):return False
    if 'cursor' in q and (len(q['cursor'][0])>1024 or not re.fullmatch(r'[A-Za-z0-9_+=:/.-]+',q['cursor'][0])):return False
    return 'with_nested_markets' not in q or q['with_nested_markets']==['true']
class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        old=urllib.parse.urlsplit(req.full_url);new=urllib.parse.urlsplit(newurl)
        if new.scheme!='https' or new.netloc!=old.netloc:raise ValueError('REDIRECT_HOST_FORBIDDEN')
        return super().redirect_request(req,fp,code,msg,headers,newurl)
def respond(path):
    path=Path(path);out=path.with_name(path.name.replace('.request.json','.response.json'));result={}
    try:
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
        with os.fdopen(fd) as f:
            st=os.fstat(f.fileno())
            if not stat.S_ISREG(st.st_mode) or st.st_size>4096:raise ValueError('REQUEST_SIZE_OR_SYMLINK')
            req=json.loads(f.read(4097))
        if set(req)!={'url'} or not isinstance(req['url'],str) or not allowed(req['url']):raise ValueError('PUBLIC_GET_ALLOWLIST_REFUSED')
        result['url']=req['url'];result['request_started_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),Redirect())
        with opener.open(urllib.request.Request(req['url'],headers={'User-Agent':'PredictionResearch-public'},method='GET'),timeout=15) as response:
            body=response.read(2_000_001)
            if len(body)>2_000_000:raise ValueError('PUBLIC_BODY_TOO_LARGE')
            result.update(ok=True,status=response.status,headers={k:v for k,v in response.headers.items() if k.lower() in ('content-type','etag','last-modified')},sha256=hashlib.sha256(body).hexdigest(),body=base64.b64encode(body).decode(),received_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    except Exception as exc:result.update(ok=False,error_type=type(exc).__name__)
    with tempfile.NamedTemporaryFile(mode='w',dir=out.parent,delete=False) as f:
        f.write(json.dumps(result));f.flush();os.fsync(f.fileno());tmp=Path(f.name)
    tmp.replace(out)
    return {k:v for k,v in result.items() if k not in ('body','headers')}
