import json
import urllib.parse
import urllib.request
base='https:'+'//external-api.kalshi.com/trade-api/v2'
def fetch(path,params=None):
 url=base+path
 if params:
  url=url+'?'+urllib.parse.urlencode(params)
 req=urllib.request.Request(url,headers={'User-Agent':'prediction-research-readonly/1.0'})
 with urllib.request.urlopen(req,timeout=20) as response:
  return response.status,json.loads(response.read().decode('utf-8'))
print('E398R1_START')
status,data=fetch('/markets',{'series_ticker':'KXTEMPMIAH','status':'open','limit':100})
markets=data.get('markets') or ()
print('MARKETS_HTTP',status)
print('OPEN_MARKET_COUNT',len(markets))
market=next(iter(markets),None)
if not isinstance(market,dict):
 raise SystemExit('NO_OPEN_MARKET')
ticker=market.get('ticker')
print('TICKER',ticker)
status,payload=fetch('/markets/'+urllib.parse.quote(str(ticker),safe='')+'/orderbook',{'depth':20})
print('ORDERBOOK_HTTP',status)
book=payload.get('orderbook_fp')
if not isinstance(book,dict):
 print('ORDERBOOK_FP_NOT_DICT')
 print('PAYLOAD_JSON',json.dumps(payload,sort_keys=True)[:5000])
 raise SystemExit(1)
print('ORDERBOOK_FP_JSON',json.dumps(book,sort_keys=True)[:10000])
print('ORDERBOOK_FP_KEYS',','.join(sorted(book.keys())))
levels=0
for name,value in book.items():
 if isinstance(value,list):
  print('SIDE',name,'LEVEL_COUNT',len(value))
  levels+=len(value)
 elif isinstance(value,dict):
  print('GROUP',name,'KEYS',','.join(sorted(value.keys())))
  for child,child_value in value.items():
   if isinstance(child_value,list):
    print('SIDE',name,child,'LEVEL_COUNT',len(child_value))
    levels+=len(child_value)
print('TOTAL_LEVELS',levels)
print('USABLE_DEPTH',levels>0)
print('E398R1_DONE')