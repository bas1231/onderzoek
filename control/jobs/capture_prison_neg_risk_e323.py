from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone
import json

root=Path.cwd()
base=root/'knowledge/raw/market_data/polymarket_neg_risk_manifests'
files=list()
if base.exists():
    for p in base.iterdir():
        if p.is_file() and p.suffix=='.json':
            files.append(p)
files.sort(key=lambda p:p.stat().st_mtime)
if not files:
    raise SystemExit('no_manifest')
manifest=json.loads(files[-1].read_text(encoding='utf-8'))
group=None
for row in manifest.get('groups') or tuple():
    if str(row.get('event_id'))=='85579':
        group=row
        break
if group is None:
    raise SystemExit('target_group_missing')

markets=group.get('markets') or tuple()
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
complete=True
for market in markets:
    yes=top(market.get('yes_token'))
    no=top(market.get('no_token'))
    if yes is None or no is None:
        complete=False
    priced.append(dict(market_id=str(market.get('market_id')),question=str(market.get('question') or ''),yes=yes,no=no))

stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
outdir=root/'knowledge/raw/market_data/polymarket_neg_risk_partial'
outdir.mkdir(parents=True,exist_ok=True)
out=outdir/(stamp+'85579.json')
payload=dict(retrieved_at=datetime.now(timezone.utc).isoformat(),event_id='85579',title=str(group.get('title') or ''),market_count=len(markets),http_status=status,live_trading=False,paid_actions=False,wallet_actions=False,complete=complete,priced=priced,books=books,markets=markets)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')

print('PRISON_NEG_RISK_CAPTURE_PASS')
print('TITLE',group.get('title'))
print('MARKET_COUNT',len(markets))
print('BOOK_COUNT',len(books))
print('COMPLETE',complete)
if complete:
    yes_ask=sum(row.get('yes').get('ask') for row in priced)
    yes_bid=sum(row.get('yes').get('bid') for row in priced)
    no_ask=sum(row.get('no').get('ask') for row in priced)
    no_bid=sum(row.get('no').get('bid') for row in priced)
    print('YES_ASK_SUM',yes_ask)
    print('YES_BID_SUM',yes_bid)
    print('NO_ASK_SUM',no_ask)
    print('NO_BID_SUM',no_bid)
    print('YES_GAP_TO_ONE',1.0-yes_ask)
    print('NO_GAP_TO_N_MINUS_ONE',float(len(priced)-1)-no_ask)
else:
    for row in priced:
        print('MARKET',row.get('market_id'),row.get('question'))
        print('YES',row.get('yes'))
        print('NO',row.get('no'))
print('PATH',out)
