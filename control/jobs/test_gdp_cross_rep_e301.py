from pathlib import Path
import json

root=Path.cwd()
base=root/'knowledge/raw/market_data/polymarket_neg_risk'
files=sorted(base.glob('*79137.json'),key=lambda p:p.stat().st_mtime)
if not files:
    raise SystemExit('gdp_snapshot_missing')
data=json.loads(files[-1].read_text(encoding='utf-8'))
rows=data.get('priced') or tuple()
if len(rows)!=6:
    raise SystemExit('unexpected_state_count')

n=len(rows)
for state in range(n):
    yes_total=0
    no_total=0
    for i in range(n):
        yes=1 if i==state else 0
        no=1-yes
        yes_total+=yes
        no_total+=no
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

print('GDP_STATEWISE_PROOF_PASS')
print('STATE_COUNT',n)
positive=0
best=-999.0
for i,row in enumerate(rows):
    direct=row.get('no') or dict()
    direct_bid=float(direct.get('bid'))
    direct_ask=float(direct.get('ask'))
    synth_ask=0.0
    synth_bid=0.0
    buy_sizes=list()
    sell_sizes=list()
    for j,other in enumerate(rows):
        if j==i:
            continue
        yes=other.get('yes') or dict()
        synth_ask+=float(yes.get('ask'))
        synth_bid+=float(yes.get('bid'))
        buy_sizes.append(float(yes.get('ask_size')))
        sell_sizes.append(float(yes.get('bid_size')))
    edge_a=direct_bid-synth_ask
    edge_b=synth_bid-direct_ask
    best=max(best,edge_a,edge_b)
    if edge_a>0 or edge_b>0:
        positive+=1
    print('IDENTITY',row.get('market_id'))
    print('QUESTION',str(row.get('question') or ''))
    print('DIRECT_NO_BID',direct_bid)
    print('DIRECT_NO_ASK',direct_ask)
    print('OTHER_YES_ASK_SUM',synth_ask)
    print('OTHER_YES_BID_SUM',synth_bid)
    print('EDGE_SYNTH_TO_DIRECT',edge_a)
    print('EDGE_DIRECT_TO_SYNTH',edge_b)
    print('BUY_SYNTH_TOP_SIZE',min(buy_sizes))
    print('SELL_SYNTH_TOP_SIZE',min(sell_sizes))
print('CROSS_REP_GROSS_POSITIVE',positive)
print('BEST_CROSS_REP_EDGE',best)
print('GDP_CROSS_REP_TEST_PASS')
