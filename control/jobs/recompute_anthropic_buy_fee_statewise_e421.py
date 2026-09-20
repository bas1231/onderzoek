from pathlib import Path
from datetime import datetime,timezone
import json
import math

root=Path.cwd()
repro_dir=root/'knowledge/raw/market_data/polymarket_reproductions'
files=[p for p in repro_dir.iterdir() if p.is_file() and p.name.endswith('-anthropic-548858-e420.json')]
files.sort(key=lambda p:p.stat().st_mtime)
if not files:
    raise SystemExit('e420_reproduction_missing')
source_path=files[-1]
data=json.loads(source_path.read_text(encoding='utf-8'))

legs=data.get('legs') or tuple()
if len(legs)!=10:
    raise SystemExit('unexpected_leg_count')
size=float(data.get('common_size'))
if size<=0:
    raise SystemExit('bad_common_size')

print('SOURCE',source_path)
print('EVENT_ID',data.get('event_id'))
print('COMMON_GROSS_SHARES_PER_LEG',size)
print('ASK_SUM',data.get('ask_sum'))

cost=0.0
states=list()
for leg in legs:
    if not isinstance(leg,dict):
        raise SystemExit('bad_leg_shape')
    price=float(leg.get('ask'))
    enabled=leg.get('fees_enabled')
    if enabled is not True:
        raise SystemExit('fee_not_enabled_'+str(leg.get('market_id')))
    rate=float(leg.get('fee_rate'))
    exponent=float(leg.get('fee_exponent'))
    if exponent!=1.0:
        raise SystemExit('unsupported_fee_exponent_'+str(leg.get('market_id')))
    if leg.get('taker_only') is not True:
        raise SystemExit('fee_not_taker_only_'+str(leg.get('market_id')))
    leg_cost=math.prod((size,price))
    cost+=leg_cost
    fee_usdc_equivalent=round(math.prod((size,rate,price,1.0-price)),5)
    fee_shares=fee_usdc_equivalent/price
    net_shares=size-fee_shares
    state_profit=net_shares
    states.append(dict(market_id=leg.get('market_id'),label=leg.get('group_item'),price=price,gross_shares=size,leg_cost_usdc=leg_cost,fee_rate=rate,fee_usdc_equivalent=fee_usdc_equivalent,fee_shares=fee_shares,net_shares_if_winner=net_shares,state_payout=state_profit))

for state in states:
    profit=float(state.get('state_payout'))-cost
    roi=profit/cost if cost>0 else None
    state['profit_after_buy_share_fee']=profit
    state['roi_after_buy_share_fee']=roi

profits=[float(state.get('profit_after_buy_share_fee')) for state in states]
payouts=[float(state.get('state_payout')) for state in states]
min_profit=min(profits)
max_profit=max(profits)
min_payout=min(payouts)
max_payout=max(payouts)
all_positive=all(value>0 for value in profits)

print('TOTAL_USDC_PURCHASE_COST',cost)
print('STATE_COUNT',len(states))
for state in states:
    print('STATE',state.get('market_id'),'LABEL',state.get('label'),'PRICE',state.get('price'),'FEE_USDC_EQ',state.get('fee_usdc_equivalent'),'FEE_SHARES',state.get('fee_shares'),'NET_WINNING_SHARES',state.get('net_shares_if_winner'),'PROFIT',state.get('profit_after_buy_share_fee'),'ROI',state.get('roi_after_buy_share_fee'))

print('MIN_STATE_PAYOUT',min_payout)
print('MAX_STATE_PAYOUT',max_payout)
print('MIN_GUARANTEED_PROFIT',min_profit)
print('MAX_STATE_PROFIT',max_profit)
print('MIN_GUARANTEED_ROI',min_profit/cost if cost>0 else None)
print('ALL_STATES_POSITIVE',all_positive)
print('E420_PRIOR_NET_TOTAL',data.get('net_total'))
print('E420_PRIOR_NET_ROI',data.get('net_roi'))
print('ACCOUNTING_NOTE','BUY taker fee modeled as share deduction using rounded USDC-equivalent fee divided by execution price')

stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
outdir=root/'knowledge/raw/market_data/polymarket_reproductions'
out=outdir/(stamp+'-anthropic-548858-e421-statewise-fees.json')
payload=dict(retrieved_at=datetime.now(timezone.utc).isoformat(),source_e420=str(source_path.relative_to(root)),event_id='548858',gross_shares_per_leg=size,total_usdc_purchase_cost=cost,min_state_payout=min_payout,max_state_payout=max_payout,min_guaranteed_profit=min_profit,max_state_profit=max_profit,min_guaranteed_roi=(min_profit/cost if cost>0 else None),all_states_positive=all_positive,fee_model='buy taker fees deducted in shares; fee USDC equivalent rounded to five decimals then divided by trade price',states=states,live_trading=False,paid_actions=False,wallet_actions=False)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')
print('OUTPUT_PATH',out)
print('ANTHROPIC_BUY_FEE_STATEWISE_E421_PASS')
