from pathlib import Path
from datetime import datetime,timezone
import json
import math

root=Path.cwd()
repro_dir=root/'knowledge/raw/market_data/polymarket_reproductions'
files=[p for p in repro_dir.iterdir() if p.is_file() and p.name.endswith('-anthropic-548858-e420.json')]
files.sort(key=lambda p:p.stat().st_mtime)
if not files:
    raise SystemExit('e420_missing')
repro_path=files[-1]
repro=json.loads(repro_path.read_text(encoding='utf-8'))
books_sha=str(repro.get('books_sha256') or '')
books_path=Path.home()/'.local/state/prediction-research/raw/polymarket_clob_books'/(books_sha+'.json')
if not books_path.exists():
    raise SystemExit('archived_books_missing')
books=json.loads(books_path.read_text(encoding='utf-8'))
if not isinstance(books,list):
    raise SystemExit('books_shape_bad')
bookmap=dict((str(book.get('asset_id')),book) for book in books if isinstance(book,dict))

legs=repro.get('legs') or tuple()
if len(legs)!=10:
    raise SystemExit('unexpected_leg_count')
size=float(repro.get('common_size'))
if size!=5.0:
    raise SystemExit('unexpected_common_size')

print('REPRO_SOURCE',repro_path)
print('BOOK_SOURCE',books_path)
print('SIZE',size)

base_prices=list()
ticks=list()
depth_ok=True
for leg in legs:
    token=str(leg.get('yes_token') or '')
    book=bookmap.get(token)
    if not isinstance(book,dict):
        raise SystemExit('book_missing_'+str(leg.get('market_id')))
    asks=book.get('asks') or tuple()
    if not asks:
        raise SystemExit('asks_missing_'+str(leg.get('market_id')))
    rows=sorted(asks,key=lambda row:float(row.get('price',9)))
    top=rows[0]
    top_price=float(top.get('price'))
    top_size=float(top.get('size',0))
    tick_raw=book.get('tick_size')
    if tick_raw is None:
        tick_raw=book.get('minimum_tick_size')
    if tick_raw is None:
        tick=0.001
        tick_source='fallback_0.001'
    else:
        tick=float(tick_raw)
        tick_source='book'
    if top_size<size:
        depth_ok=False
    base_prices.append(top_price)
    ticks.append(tick)
    print('LEG',leg.get('market_id'),'LABEL',leg.get('group_item'),'TOP_ASK',top_price,'TOP_SIZE',top_size,'TICK',tick,'TICK_SOURCE',tick_source,'ASK_LEVELS',len(rows))

print('ALL_TOP_LEVEL_DEPTH_AT_LEAST_5',depth_ok)
print('BASE_ASK_SUM',sum(base_prices))
print('TOTAL_ONE_TICK_COST_SHIFT',math.prod((size,sum(ticks))))
print('TOTAL_TWO_TICK_COST_SHIFT',math.prod((size,2.0,sum(ticks))))

def evaluate(label,prices):
    purchase_cost=math.prod((size,sum(prices)))
    states=list()
    for index,leg in enumerate(legs):
        p=float(prices[index])
        rate=float(leg.get('fee_rate'))
        exponent=float(leg.get('fee_exponent'))
        if leg.get('fees_enabled') is not True or exponent!=1.0 or leg.get('taker_only') is not True:
            raise SystemExit('unsupported_fee_schedule_'+str(leg.get('market_id')))
        fee_usdc=round(math.prod((size,rate,p,1.0-p)),5)
        fee_shares=fee_usdc/p
        net_shares=size-fee_shares
        profit=net_shares-purchase_cost
        roi=profit/purchase_cost if purchase_cost>0 else None
        states.append(dict(market_id=leg.get('market_id'),label=leg.get('group_item'),price=p,fee_usdc_equivalent=fee_usdc,fee_shares=fee_shares,net_winning_shares=net_shares,profit=profit,roi=roi))
    profits=[float(row.get('profit')) for row in states]
    result=dict(label=label,purchase_cost=purchase_cost,ask_sum=sum(prices),min_profit=min(profits),max_profit=max(profits),min_roi=(min(profits)/purchase_cost if purchase_cost>0 else None),all_states_positive=all(value>0 for value in profits),states=states)
    print('SCENARIO',label)
    print('ASK_SUM',result.get('ask_sum'))
    print('PURCHASE_COST',purchase_cost)
    print('MIN_PROFIT',result.get('min_profit'))
    print('MAX_PROFIT',result.get('max_profit'))
    print('MIN_ROI',result.get('min_roi'))
    print('ALL_STATES_POSITIVE',result.get('all_states_positive'))
    return result

base=evaluate('BASE',base_prices)
one_prices=[min(0.999,float(base_prices[i])+float(ticks[i])) for i in range(len(base_prices))]
two_prices=[min(0.999,float(base_prices[i])+math.prod((2.0,float(ticks[i])))) for i in range(len(base_prices))]
one=evaluate('ALL_LEGS_ONE_TICK_WORSE',one_prices)
two=evaluate('ALL_LEGS_TWO_TICKS_WORSE',two_prices)

single_results=list()
for index in range(len(base_prices)):
    prices=list(base_prices)
    prices[index]=min(0.999,float(prices[index])+float(ticks[index]))
    result=evaluate('ONE_LEG_ONE_TICK_WORSE_'+str(legs[index].get('market_id')),prices)
    single_results.append(result)

worst_single=min(float(row.get('min_profit')) for row in single_results)
print('WORST_SINGLE_LEG_ONE_TICK_MIN_PROFIT',worst_single)
print('BASE_SURVIVES',base.get('all_states_positive'))
print('ALL_LEGS_ONE_TICK_SURVIVES',one.get('all_states_positive'))
print('ALL_LEGS_TWO_TICKS_SURVIVES',two.get('all_states_positive'))
print('ANY_SINGLE_LEG_ONE_TICK_FAILS',any(not row.get('all_states_positive') for row in single_results))

stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out=repro_dir/(stamp+'-anthropic-548858-e422-execution-stress.json')
payload=dict(retrieved_at=datetime.now(timezone.utc).isoformat(),source_e420=str(repro_path.relative_to(root)),books_sha256=books_sha,size=size,all_top_level_depth_at_least_5=depth_ok,ticks=ticks,base=base,all_legs_one_tick_worse=one,all_legs_two_ticks_worse=two,single_leg_one_tick_worse=single_results,worst_single_leg_one_tick_min_profit=worst_single,live_trading=False,paid_actions=False,wallet_actions=False)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')
print('OUTPUT_PATH',out)
print('ANTHROPIC_EXECUTION_STRESS_E422_PASS')
