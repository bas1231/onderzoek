from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone
import json

root=Path.cwd()
files=sorted((root/'knowledge/raw/market_data/polymarket_neg_risk_manifests').glob('*.json'),key=lambda p:p.stat().st_mtime)
if not files:
    raise SystemExit('no_manifest')
manifest=json.loads(files[-1].read_text(encoding='utf-8'))
targets={'51456','79137','79905','86426','102763'}
groups=[]
for group in manifest.get('groups',[]):
    if str(group.get('event_id')) in targets:
        groups.append(group)
if len(groups)!=len(targets):
    raise SystemExit('target_group_missing')

url='https:'+chr(47)+chr(47)+'clob.polymarket.com/books'
agent='PredictionEdgeHunter/1.0'
results=[]

for group in groups:
    tokens=[]
    for market in group['markets']:
        tokens.append({'token_id':market})
        tokens.append({'token_id':market})
    body=json.dumps(tokens).encode('utf-8')
    req=Request(url,data=body,headers={'Content-Type':'application/json','User-Agent':agent},method='POST')
    try:
        with urlopen(req,timeout=30) as r:
            books=json.loads(r.read())
    except Exception as exc:
        results.append({'event_id':group,'title':group,'status':'BOOK_FETCH_FAILED','error':str(exc)})
        continue
    bookmap={str(b.get('asset_id')):b for b in books}
    priced=[]
    complete=True
    for market in group['markets']:
        row={'market_id':market,'question':market}
        for side in ['yes','no']:
            token=market[side+'_token']
            book=bookmap.get(token)
            if not book:
                complete=False
                break
            bids=book.get('bids') or []
            asks=book.get('asks') or []
            if not bids or not asks:
                complete=False
                break
            bid=max(bids,key=lambda x:float(x.get('price',0)))
            ask=min(asks,key=lambda x:float(x.get('price',9)))
            row[side]={'bid':float(bid.get('price')),'bid_size':float(bid.get('size',0)),'ask':float(ask.get('price')),'ask_size':float(ask.get('size',0))}
        if not complete:
            break
        priced.append(row)
    if not complete or len(priced)!=len(group['markets']):
        results.append({'event_id':group,'title':group,'status':'INCOMPLETE_BOOKS','market_count':len(group['markets']),'returned_books':len(books)})
        continue
    n=len(priced)
    yes_ask=sum(r['yes']['ask'] for r in priced)
    yes_bid=sum(r['yes']['bid'] for r in priced)
    no_ask=sum(r['no']['ask'] for r in priced)
    no_bid=sum(r['no']['bid'] for r in priced)
    results.append({'event_id':group,'title':group,'status':'PRICED','market_count':n,'yes_ask_cost':yes_ask,'yes_bid_sum':yes_bid,'yes_gross_edge':1.0-yes_ask,'yes_top_size':min(r['yes']['ask_size'] for r in priced),'no_ask_cost':no_ask,'no_bid_sum':no_bid,'no_gross_edge':float(n-1)-no_ask,'no_top_size':min(r['no']['ask_size'] for r in priced)})

stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
outdir=root/'knowledge/raw/market_data/polymarket_neg_risk_scans'
outdir.mkdir(parents=True,exist_ok=True)
out=outdir/(stamp+'batch_e297.json')
out.write_text(json.dumps({'retrieved_at':datetime.now(timezone.utc).isoformat(),'live_trading':False,'paid_actions':False,'wallet_actions':False,'results':results},indent=2,sort_keys=True)+chr(10),encoding='utf-8')

print('NEG_RISK_BATCH_PRICE_PASS')
for row in results:
    print('GROUP',row['event_id'],row['status'],row['title'][:160])
    if row['status']=='PRICED':
        print('MARKETS',row['market_count'],'YES_EDGE',row['yes_gross_edge'],'YES_SIZE',row['yes_top_size'],'NO_EDGE',row['no_gross_edge'],'NO_SIZE',row['no_top_size'])
positive=[r for r in results if r.get('status')=='PRICED' and (r.get('yes_gross_edge',0)>0 or r.get('no_gross_edge',0)>0)]
print('GROSS_POSITIVE_GROUPS',len(positive))
print('PATH',out)
