from pathlib import Path
from urllib.request import Request,urlopen
import json

root=Path.cwd()
files=sorted((root/'knowledge/raw/market_data/polymarket_neg_risk_partial').glob('_51456.json'),key=lambda p:p.stat().st_mtime)
if not files:
    raise SystemExit('fed_snapshot_missing')
snap=json.loads(files[-1].read_text(encoding='utf-8'))
markets=snap.get('markets') or tuple()
books=snap.get('books') or tuple()
bookmap=dict((str(book.get('asset_id')),book) for book in books)

url='https:'+chr(47)+chr(47)+'gamma-api.polymarket.com/events/51456'
req=Request(url,headers={'User-Agent':'PredictionEdgeHunter/1.0'})
with urlopen(req,timeout=30) as r:
    event=json.loads(r.read())
current=dict((str(m.get('id')),m) for m in (event.get('markets') or tuple()))

prices=list()
rates=list()
exponents=list()
for market in markets:
    mid=str(market.get('market_id'))
    live=current.get(mid) or dict()
    enabled=live.get('feesEnabled')
    schedule=live.get('feeSchedule') or dict()
    rate=schedule.get('rate')
    exponent=schedule.get('exponent')
    delay=live.get('secondsDelay')
    min_size=live.get('orderMinSize')
    tick=live.get('orderPriceMinTickSize')
    print('MARKET',mid)
    print('FEES_ENABLED',enabled)
    print('FEE_RATE',rate)
    print('FEE_EXPONENT',exponent)
    print('TAKER_ONLY',schedule.get('takerOnly'))
    print('REBATE_RATE',schedule.get('rebateRate'))
    print('SECONDS_DELAY',delay)
    print('ORDER_MIN_SIZE',min_size)
    print('TICK_SIZE',tick)
    if enabled is not True or rate is None:
        raise SystemExit('fee_configuration_unproven')
    rates.append(float(rate))
    exponents.append(float(exponent if exponent is not None else 1))
    token=str(market.get('yes_token'))
    book=bookmap.get(token) or dict()
    asks=book.get('asks') or tuple()
    if not asks:
        raise SystemExit('yes_ask_missing')
    ask=min(float(x.get('price')) for x in asks)
    prices.append(ask)

if max(rates)-min(rates)>0.0000001:
    raise SystemExit('fee_rates_differ')
if max(exponents)-min(exponents)>0.0000001:
    raise SystemExit('fee_exponents_differ')
rate=rates[0]
exponent=exponents[0]
if exponent!=1.0:
    raise SystemExit('unsupported_fee_exponent')

gross_per_set=1.0-sum(prices)
fee_per_set=sum(ratep*(1.0-p) for p in prices)
net_per_set=gross_per_set-fee_per_set
size=75.0
gross_size=gross_per_setsize
fee_size=sum(sizeratep(1.0-p) for p in prices)
net_size=gross_size-fee_size
rounded_fee_size=sum(round(sizeratep*(1.0-p),5) for p in prices)
rounded_net_size=gross_size-rounded_fee_size

print('PRICE_COUNT',len(prices))
print('ASK_SUM',sum(prices))
print('GROSS_EDGE_PER_SET',gross_per_set)
print('TAKER_FEE_RATE',rate)
print('UNROUNDED_FEE_PER_SET',fee_per_set)
print('UNROUNDED_NET_PER_SET',net_per_set)
print('SIZE_TESTED',size)
print('GROSS_EDGE_AT_SIZE',gross_size)
print('UNROUNDED_FEES_AT_SIZE',fee_size)
print('UNROUNDED_NET_AT_SIZE',net_size)
print('ROUNDED_FEES_AT_SIZE',rounded_fee_size)
print('ROUNDED_NET_AT_SIZE',rounded_net_size)
if rounded_net_size<=0:
    print('KILL_RESULT','KILLED_BY_TAKER_FEES')
elif rounded_net_size<0.01:
    print('KILL_RESULT','ECONOMICALLY_NEGLIGIBLE_AFTER_FEES')
else:
    print('KILL_RESULT','SURVIVES_FEE_GATE_ONLY')
print('FED_FEE_KILL_TEST_PASS')
