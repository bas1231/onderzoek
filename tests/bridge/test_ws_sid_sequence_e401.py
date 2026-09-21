from pathlib import Path
import sys

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / 'control' / 'weather'))

from market_reaction import OrderBook
from kalshi_market_reaction_ws import validate_subscription_sequence

tracker = {}
a = OrderBook('A')
b = OrderBook('B')

snap_a = {'type': 'orderbook_snapshot', 'sid': 7, 'seq': 2, 'msg': {'market_ticker': 'A', 'yes_dollars_fp': [['0.40', '5']], 'no_dollars_fp': [['0.50', '4']]}}
snap_b = {'type': 'orderbook_snapshot', 'sid': 7, 'seq': 3, 'msg': {'market_ticker': 'B', 'yes_dollars_fp': [['0.30', '6']], 'no_dollars_fp': [['0.60', '3']]}}
delta_a = {'type': 'orderbook_delta', 'sid': 7, 'seq': 4, 'msg': {'market_ticker': 'A', 'side': 'yes', 'price_dollars': '0.40', 'delta_fp': '1'}}

validate_subscription_sequence(tracker, snap_a)
a.snapshot(snap_a, '2026-09-21T15:00:00+00:00')
validate_subscription_sequence(tracker, snap_b)
b.snapshot(snap_b, '2026-09-21T15:00:00.010000+00:00')
validate_subscription_sequence(tracker, delta_a)
# OrderBook no longer enforces per-ticker seq+1; subscription tracker does.
state = a.delta(delta_a, '2026-09-21T15:00:00.020000+00:00')
assert tracker[7] == 4
assert str(state.yes_bid_qty) == '6'

failed = False
try:
    validate_subscription_sequence(tracker, {'type': 'orderbook_delta', 'sid': 7, 'seq': 6, 'msg': {'market_ticker': 'A'}})
except ValueError:
    failed = True
assert failed
