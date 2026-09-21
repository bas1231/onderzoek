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
print('E397_START')
status,data=fetch('/markets',{'series_ticker':'KXTEMPMIAH','status':'open','limit':100})
markets=data.get('markets') or []
print('MARKETS_HTTP',status)
print('OPEN_MARKET_COUNT',len(markets))
if not markets:
 raise SystemExit('NO_OPEN_KXTEMPMIAH_MARKET')
market=markets[0]
ticker=market.get('ticker')
print('PROBE_TICKER',ticker)
print('TOP_YES_BID',market.get('yes_bid_dollars'))
print('TOP_YES_ASK',market.get('yes_ask_dollars'))
print('TOP_YES_BID_SIZE',market.get('yes_bid_size_fp'))
print('TOP_YES_ASK_SIZE',market.get('yes_ask_size_fp'))
status,book=fetch('/markets/'+urllib.parse.quote(str(ticker),safe='')+'/orderbook',{'depth':10})
print('ORDERBOOK_HTTP',status)
print('ORDERBOOK_TOP_KEYS',sorted(book.keys()))
orderbook=book.get('orderbook') or book
print('ORDERBOOK_KEYS',sorted(orderbook.keys()) if isinstance(orderbook,dict) else type(orderbook).name)
if isinstance(orderbook,dict):
 for name,value in orderbook.items():
  if isinstance(value,list):
   print('BOOK_SIDE',name,'LEVEL_COUNT',len(value),'SAMPLE',value[:3])
print('E397_PUBLIC_L2_PROBE_PASS')