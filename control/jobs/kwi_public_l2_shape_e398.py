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
print('E398_START')
status,data=fetch('/markets',{'series_ticker':'KXTEMPMIAH','status':'open','limit':100})
markets=data.get('markets') or ()
print('MARKETS_HTTP',status)
print('OPEN_MARKET_COUNT',len(markets))
market=next(iter(markets),None)
if not isinstance(market,dict):
 raise SystemExit('NO_OPEN_MARKET')
ticker=market.get('ticker')
print('TICKER',ticker)
print('MARKET_TOP_YES_BID',market.get('yes_bid_dollars'))
print('MARKET_TOP_YES_ASK',market.get('yes_ask_dollars'))
status,payload=fetch('/markets/'+urllib.parse.quote(str(ticker),safe='')+'/orderbook',{'depth':20})
print('ORDERBOOK_HTTP',status)
book=payload.get('orderbook_fp')
print('ORDERBOOK_FP_TYPE',type(book).name)
if not isinstance(book,dict):
 print('PAYLOAD_KEYS',sorted(payload.keys()))
 raise SystemExit('ORDERBOOK_FP_NOT_DICT')
print('ORDERBOOK_FP_KEYS',sorted(book.keys()))
level_total=0
for side,value in book.items():
 print('SIDE',side,'TYPE',type(value).name)
 if isinstance(value,list):
  print('SIDE_LEVEL_COUNT',side,len(value))
  for level in value[:5]:
   print('LEVEL',side,repr(level))
  level_total+=len(value)
 elif isinstance(value,dict):
  print('SIDE_KEYS',side,sorted(value.keys()))
  for child,levels in value.items():
   print('CHILD',side,child,'TYPE',type(levels).name)
   if isinstance(levels,list):
    print('CHILD_LEVEL_COUNT',side,child,len(levels))
    for level in levels[:5]:
     print('LEVEL',side,child,repr(level))
    level_total+=len(levels)
print('TOTAL_LEVELS',level_total)
print('USABLE_DEPTH',level_total>0)
print('E398_DONE')