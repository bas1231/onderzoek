from pathlib import Path
from datetime import datetime,timezone,timedelta
import hashlib
import json
import urllib.parse
import urllib.request

BASE='https:'+'//external-api.kalshi.com/trade-api/v2'
OUT=Path.home()/'.local/state/prediction-research/kxtemp_l2_snapshots'
USER_AGENT='prediction-research-readonly/1.0'

def now_utc():
 return datetime.now(timezone.utc)

def parse_time(value):
 if not value:
  return None
 try:
  return datetime.fromisoformat(str(value).replace('Z','+00:00'))
 except Exception:
  return None

def fetch(path,params=None):
 url=BASE+path
 if params:
  url=url+'?'+urllib.parse.urlencode(params)
 req=urllib.request.Request(url,headers={'User-Agent':USER_AGENT})
 with urllib.request.urlopen(req,timeout=20) as response:
  body=response.read().decode('utf-8')
  return response.status,json.loads(body)

def discover_open_markets():
 markets=[]
 cursor=None
 pages=0
 while True:
  params={'status':'open','limit':1000}
  if cursor:
   params['cursor']=cursor
  status,data=fetch('/markets',params)
  if status!=200:
   raise RuntimeError('MARKETS_HTTP_'+str(status))
  markets.extend(data.get('markets') or ())
  pages+=1
  cursor=data.get('cursor')
  if not cursor or pages>=10:
   break
 return markets,pages

def main():
 started=now_utc()
 all_markets,pages=discover_open_markets()
 horizon=started+timedelta(minutes=90)
 selected=[]
 for market in all_markets:
  if not isinstance(market,dict):
   continue
  ticker=str(market.get('ticker') or '')
  if not ticker.startswith('KXTEMP'):
   continue
  close_time=parse_time(market.get('close_time'))
  if close_time is None:
   continue
  if close_time<started-timedelta(minutes=5):
   continue
  if close_time>horizon:
   continue
  selected.append(market)
 if not selected:
  raise SystemExit('NO_NEAR_TERM_KXTEMP_MARKETS')
 if len(selected)>80:
  raise SystemExit('TOO_MANY_SELECTED_MARKETS_'+str(len(selected)))
 books=[]
 nonempty=0
 for market in selected:
  ticker=str(market.get('ticker'))
  path='/markets/'+urllib.parse.quote(ticker,safe='')+'/orderbook'
  status,payload=fetch(path,{'depth':50})
  book=payload.get('orderbook_fp') if isinstance(payload,dict) else None
  if isinstance(book,dict):
   yes_levels=book.get('yes_dollars') or ()
   no_levels=book.get('no_dollars') or ()
   if yes_levels or no_levels:
    nonempty+=1
  books.append({'ticker':ticker,'http_status':status,'orderbook_fp':book})
 finished=now_utc()
 record={
  'schema':'KXTEMP_L2_SNAPSHOT_V1',
  'retrieved_started_at':started.isoformat(),
  'retrieved_finished_at':finished.isoformat(),
  'source':'Kalshi public Trade API v2',
  'authenticated':False,
  'live_trading':False,
  'discovery_pages':pages,
  'open_market_count':len(all_markets),
  'selected_market_count':len(selected),
  'selected_markets':selected,
  'books':books
 }
 canonical=json.dumps(record,sort_keys=True,separators=(',',':')).encode('utf-8')
 digest=hashlib.sha256(canonical).hexdigest()
 envelope={'sha256':digest,'record':record}
 OUT.mkdir(parents=True,exist_ok=True)
 stamp=started.strftime('%Y%m%dT%H%M%S%fZ')
 target=OUT/(stamp+'-'+digest[:12]+'.json')
 if target.exists():
  raise SystemExit('IMMUTABLE_TARGET_EXISTS')
 target.write_text(json.dumps(envelope,sort_keys=True,indent=2)+'
',encoding='utf-8')
 events=set()
 series=set()
 for market in selected:
  event=str(market.get('event_ticker') or '')
  ser=str(market.get('series_ticker') or '')
  if event:
   events.add(event)
  if ser:
   series.add(ser)
 print('KXTEMP_L2_RECORDER_E399_PASS')
 print('OPEN_MARKETS',len(all_markets))
 print('DISCOVERY_PAGES',pages)
 print('SELECTED_MARKETS',len(selected))
 print('SELECTED_EVENTS',len(events))
 print('SELECTED_SERIES',len(series))
 print('NONEMPTY_BOOKS',nonempty)
 print('API_REQUESTS',pages+len(selected))
 print('SNAPSHOT_SHA256',digest)
 print('SNAPSHOT_PATH',target)

if name=='main':
 main()
