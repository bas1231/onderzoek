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
    if str(row.get('event_id'))=='51456':
        group=row
        break
if group is None:
    raise SystemExit('fed_group_missing')

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

stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
outdir=root/'knowledge/raw/market_data/polymarket_neg_risk_partial'
outdir.mkdir(parents=True,exist_ok=True)
out=outdir/(stamp+'_51456.json')
payload=dict(retrieved_at=datetime.now(timezone.utc).isoformat(),event_id='51456',title=str(group.get('title') or ''),http_status=status,live_trading=False,paid_actions=False,wallet_actions=False,markets=markets,books=books)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')

complete=0
missing=0
one_sided=0
for market in markets:
    print('MARKET',market.get('market_id'),str(market.get('question') or '')[:180])
    for side in ['yes','no']:
        token=str(market.get(side+'_token'))
        book=bookmap.get(token)
        if not book:
            missing+=1
            print('SIDE',side.upper(),'MISSING_BOOK')
            continue
        bids=book.get('bids') or tuple()
        asks=book.get('asks') or tuple()
        if bids and asks:
            complete+=1
            bid=max(float(x.get('price')) for x in bids)
            ask=min(float(x.get('price')) for x in asks)
            print('SIDE',side.upper(),'COMPLETE','BIDS',len(bids),'ASKS',len(asks),'BID',bid,'ASK',ask)
        else:
            one_sided+=1
            print('SIDE',side.upper(),'ONE_SIDED','BIDS',len(bids),'ASKS',len(asks))
print('REQUESTED_BOOKS',len(tokens))
print('RETURNED_BOOKS',len(books))
print('COMPLETE_SIDES',complete)
print('MISSING_SIDES',missing)
print('ONE_SIDED_SIDES',one_sided)
print('PATH',out)
print('FED_BOOK_INSPECTION_PASS')
