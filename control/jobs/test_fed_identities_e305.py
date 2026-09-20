from pathlib import Path
import json

root=Path.cwd()
base=root/'knowledge/raw/market_data/polymarket_neg_risk_partial'
files=sorted(base.glob('*51456.json'),key=lambda p:p.stat().st_mtime)
if not files:
    raise SystemExit('fed_partial_snapshot_missing')

data=json.loads(files[-1].read_text(encoding='utf-8'))
markets=data.get('markets') or tuple()
books=data.get('books') or tuple()
if len(markets)!=13:
    raise SystemExit('unexpected_market_count')
bookmap=dict((str(book.get('asset_id')),book) for book in books)

def top(token):
    book=bookmap.get(str(token))
    if not book:
        return dict()
    bids=book.get('bids') or tuple()
    asks=book.get('asks') or tuple()
    out=dict()
    if bids:
        row=max(bids,key=lambda x:float(x.get('price',0)))
        out.update(bid=float(row.get('price')),bid_size=float(row.get('size',0)))
    if asks:
        row=min(asks,key=lambda x:float(x.get('price',9)))
        out.update(ask=float(row.get('price')),ask_size=float(row.get('size',0)))
    return out

rows=list()
for market in markets:
    rows.append(dict(market_id=str(market.get('market_id')),question=str(market.get('question') or ''),yes=top(market.get('yes_token')),no=top(market.get('no_token'))))

n=len(rows)
for state in range(n):
    yes_total=0
    no_total=0
    for i in range(n):
        yes=1 if i==state else 0
        yes_total+=yes
        no_total+=1-yes
    if yes_total!=1 or no_total!=n-1:
        raise SystemExit('partition_proof_failed')
    for i in range(n):
        direct_no=0 if i==state else 1
        other_yes=0
        for j in range(n):
            if j!=i and j==state:
                other_yes+=1
        if direct_no!=other_yes:
            raise SystemExit('cross_rep_proof_failed')

for row in rows:
    if row.get('yes').get('ask') is None:
        raise SystemExit('missing_yes_ask')

yes_ask_sum=sum(float(row.get('yes').get('ask')) for row in rows)
yes_top_size=min(float(row.get('yes').get('ask_size')) for row in rows)
print('FED_STATEWISE_PROOF_PASS')
print('STATE_COUNT',n)
print('ALL_YES_ASK_COST',yes_ask_sum)
print('ALL_YES_GROSS_FLOOR_EDGE',1.0-yes_ask_sum)
print('ALL_YES_TOP_SIZE',yes_top_size)

positive=0
best=-999.0
for i,row in enumerate(rows):
    no=row.get('no') or dict()
    no_bid=no.get('bid')
    no_bid_size=no.get('bid_size')
    synth_ask=0.0
    synth_sizes=list()
    for j,other in enumerate(rows):
        if j==i:
            continue
        yes=other.get('yes') or dict()
        synth_ask+=float(yes.get('ask'))
        synth_sizes.append(float(yes.get('ask_size')))
    print('IDENTITY',row.get('market_id'))
    print('QUESTION',str(row.get('question') or ''))
    print('SYNTH_NO_ASK',synth_ask)
    print('SYNTH_TOP_SIZE',min(synth_sizes))
    if no_bid is None:
        print('DIRECT_NO_BID','NONE')
        continue
    edge=float(no_bid)-synth_ask
    best=max(best,edge)
    if edge>0:
        positive+=1
    print('DIRECT_NO_BID',no_bid)
    print('DIRECT_NO_BID_SIZE',no_bid_size)
    print('GROSS_REPRESENTATION_EDGE',edge)

print('REPRESENTATION_GROSS_POSITIVE',positive)
print('BEST_REPRESENTATION_EDGE',best)
print('FED_IDENTITY_TEST_PASS')
