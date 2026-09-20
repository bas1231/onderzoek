from pathlib import Path
import json

root=Path.cwd()
price_path=root/'knowledge/raw/market_data/polymarket_neg_risk/20260920T013232Z86426.json'
rule_path=root/'knowledge/raw/market_rules/polymarket/20260920T013304Zevent_86426.json'
if not price_path.exists():
    raise SystemExit('price_snapshot_missing')
if not rule_path.exists():
    raise SystemExit('rule_snapshot_missing')

prices=json.loads(price_path.read_text(encoding='utf-8'))
event=json.loads(rule_path.read_text(encoding='utf-8'))
rows=prices.get('priced') or tuple()
rules=event.get('markets') or tuple()
if len(rows)!=7 or len(rules)!=7:
    raise SystemExit('market_count_wrong')

if event.get('negRisk') is not True:
    raise SystemExit('event_not_neg_risk')
if event.get('negRiskAugmented') is not False:
    raise SystemExit('unexpected_augmented_flag')
group=str(event.get('negRiskMarketID') or '')
if not group:
    raise SystemExit('neg_risk_group_missing')
for rule in rules:
    if rule.get('negRisk') is not True:
        raise SystemExit('market_not_neg_risk')
    if rule.get('negRiskOther') is not False:
        raise SystemExit('unexpected_other_flag')

print('ARCTIC_STRUCTURAL_NEG_RISK_PASS')
print('NEG_RISK_MARKET_ID',group)

pos_a=0
pos_b=0
best_a=-999.0
best_b=-999.0
for i,row in enumerate(rows):
    no=row.get('no') or dict()
    no_bid=float(no.get('bid'))
    no_ask=float(no.get('ask'))
    no_bid_size=float(no.get('bid_size'))
    no_ask_size=float(no.get('ask_size'))
    synth_ask=0.0
    synth_bid=0.0
    ask_sizes=list()
    bid_sizes=list()
    for j,other in enumerate(rows):
        if j==i:
            continue
        yes=other.get('yes') or dict()
        synth_ask+=float(yes.get('ask'))
        synth_bid+=float(yes.get('bid'))
        ask_sizes.append(float(yes.get('ask_size')))
        bid_sizes.append(float(yes.get('bid_size')))
    edge_a=no_bid-synth_ask
    edge_b=synth_bid-no_ask
    if edge_a>0:
        pos_a+=1
    if edge_b>0:
        pos_b+=1
    best_a=max(best_a,edge_a)
    best_b=max(best_b,edge_b)
    print('IDENTITY',row.get('market_id'))
    print('QUESTION',row.get('question'))
    print('SYNTH_ASK',synth_ask)
    print('DIRECT_NO_BID',no_bid)
    print('EDGE_SYNTH_BUY_DIRECT_SELL',edge_a)
    print('TOP_SIZE_A',min(min(ask_sizes),no_bid_size))
    print('SYNTH_BID',synth_bid)
    print('DIRECT_NO_ASK',no_ask)
    print('EDGE_DIRECT_BUY_SYNTH_SELL',edge_b)
    print('TOP_SIZE_B',min(min(bid_sizes),no_ask_size))

print('POSITIVE_DIRECTION_A',pos_a)
print('POSITIVE_DIRECTION_B',pos_b)
print('BEST_DIRECTION_A',best_a)
print('BEST_DIRECTION_B',best_b)
if pos_a==0 and pos_b==0:
    print('RESULT','NO_GROSS_CROSS_REPRESENTATION_EDGE')
else:
    print('RESULT','GROSS_CANDIDATE_REQUIRES_DEEPER_PROOF')
print('ARCTIC_CROSS_REP_TEST_PASS')
