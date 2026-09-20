from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone
import json

root=Path.cwd()
files=sorted((root/'knowledge/raw/market_data/polymarket_neg_risk_manifests').glob('*.json'),key=lambda p:p.stat().st_mtime)
if not files:
    raise SystemExit('no_manifest')
manifest=json.loads(files[-1].read_text(encoding='utf-8'))
group=None
for row in manifest.get('groups',tuple()):
    if str(row.get('event_id'))=='79137':
        group=row
        break
if group is None:
    raise SystemExit('gdp_group_missing')

markets=group.get('markets',tuple())
tokens=list()
for market in markets:
    tokens.append(dict(token_id=str(market.get('yes_token'))))
    tokens.append(dict(token_id=str(market.get('no_token'))))

url='https:'+chr(47)+chr(47)+'clob.polymarket.com/books'
body=json.dumps(tokens).encode('utf-8')
req=Request(url,data=body,headers={'Content-Type':'application/json','User-Agent':'PredictionEdgeHunter/1.0'},method='POST')
with urlopen(req,timeout=30) as r:
    books=json.loads(r.read())
    status=r.status
bookmap=dict((str(book.get('asset_id')),book) for book in books)

def top(token):
    book=bookmap.get(str(token))
    if not book:
        return None
    bids=book.get('bids') or tuple()
    asks=book.get('asks') or tuple()
    if not bids or not asks:
        return None
    bid=max(bids,key=lambda x:float(x.get('price',0)))
    ask=min(asks,key=lambda x:float(x.get('price',9)))
    return dict(bid=float(bid.get('price')),bid_size=float(bid.get('size',0)),ask=float(ask.get('price')),ask_size=float(ask.get('size',0)))

priced=list()
for market in markets:
    yes=top(market.get('yes_token'))
    no=top(market.get('no_token'))
    if yes is None or no is None:
        raise SystemExit('incomplete_book')
    priced.append(dict(market_id=str(market.get('market_id')),question=str(market.get('question') or ''),yes=yes,no=no))

n=len(priced)
yes_ask=sum(row.get('yes').get('ask') for row in priced)
yes_bid=sum(row.get('yes').get('bid') for row in priced)
no_ask=sum(row.get('no').get('ask') for row in priced)
no_bid=sum(row.get('no').get('bid') for row in priced)
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
outdir=root/'knowledge/raw/market_data/polymarket_neg_risk'
outdir.mkdir(parents=True,exist_ok=True)
out=outdir/(stamp+'79137.json')
payload=dict(retrieved_at=datetime.now(timezone.utc).isoformat(),event_id='79137',title=str(group.get('title') or ''),neg_risk_market_id=str(group.get('neg_risk_market_id') or ''),market_count=n,http_status=status,live_trading=False,paid_actions=False,wallet_actions=False,priced=priced,yes_ask_sum=yes_ask,yes_bid_sum=yes_bid,no_ask_sum=no_ask,no_bid_sum=no_bid)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')

print('GDP_NEG_RISK_CAPTURE_PASS')
print('MARKET_COUNT',n)
print('BOOK_COUNT',len(books))
print('YES_ASK_SUM',yes_ask)
print('YES_BID_SUM',yes_bid)
print('NO_ASK_SUM',no_ask)
print('NO_BID_SUM',no_bid)
print('YES_GAP_TO_ONE',1.0-yes_ask)
print('NO_GAP_TO_N_MINUS_ONE',float(n-1)-no_ask)
print('PATH',out)
