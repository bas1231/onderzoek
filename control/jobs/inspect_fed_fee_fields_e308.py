from urllib.request import Request,urlopen
import json

url='https:'+chr(47)+chr(47)+'gamma-api.polymarket.com/events/51456'
req=Request(url,headers={'User-Agent':'PredictionEdgeHunter/1.0'})
with urlopen(req,timeout=30) as r:
    event=json.loads(r.read())

print('EVENT_ID',event.get('id'))
print('TITLE',event.get('title'))
for market in event.get('markets') or tuple():
    print('MARKET',market.get('id'),str(market.get('question') or '')[:180])
    found=0
    for key in sorted(market.keys()):
        low=key.lower()
        if 'fee' in low or 'delay' in low or 'tick' in low or 'order' in low or 'maker' in low or 'taker' in low:
            print('FIELD',key,str(market.get(key))[:1000])
            found+=1
    print('FEE_FIELDS_FOUND',found)
    print('---')
print('FED_FEE_FIELD_INSPECTION_PASS')
