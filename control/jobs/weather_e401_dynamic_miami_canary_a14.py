from pathlib import Path
import json
import os
import subprocess
import urllib.parse
import urllib.request

ROOT = Path.cwd()
PYTHON = ROOT / '.venv' / 'bin' / 'python'
ENV_FILE = Path.home() / '.config' / 'prediction-research' / 'kalshi_readonly.env'
BASE = 'https://external-api.kalshi.com/trade-api/v2'
SERIES = 'KXTEMPMIAH'

result = {
    'task': 'EDGE-HUNTER-KWI-MIAMI-WS-CANARY-E401A14',
    'series': SERIES,
    'event_ticker': None,
    'ticker_count': 0,
    'ws_connected': False,
    'snapshot_frames': 0,
    'delta_frames': 0,
    'reconstructed_delta_states': 0,
    'market_state_events': 0,
    'trade_frames': 0,
    'capture_gaps': 0,
    'capture_errors': 0,
    'live_trading': False,
    'paid_action': False,
    'wallet_action': False,
    'economic_conclusion': 'NO_PROVEN_EDGE'
}

if not ENV_FILE.is_file():
    result['status'] = 'BLOCKED_ENV_MISSING'
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(10)

for line in ENV_FILE.read_text(encoding='utf-8').splitlines():
    line = line.strip()
    if not line or line.startswith('#'):
        continue
    key, sep, value = line.partition('=')
    if sep and key:
        os.environ[key] = value

params = urllib.parse.urlencode({
    'series_ticker': SERIES,
    'status': 'open',
    'limit': 200,
    'with_nested_markets': 'true'
})
req = urllib.request.Request(
    BASE + '/events?' + params,
    headers={'User-Agent': 'PredictionResearch-KWI-canary/1'},
    method='GET'
)
with urllib.request.urlopen(req, timeout=15) as response:
    payload = json.loads(response.read().decode('utf-8'))

events = [event for event in payload.get('events', []) if event.get('markets')]
if not events:
    result['status'] = 'BLOCKED_NO_OPEN_MIAMI_EVENT'
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(11)

event = events[0]
tickers = sorted({market.get('ticker') for market in event.get('markets', []) if market.get('ticker')})
result['event_ticker'] = event.get('event_ticker')
result['ticker_count'] = len(tickers)

if not tickers:
    result['status'] = 'BLOCKED_NO_MARKETS'
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(12)

cmd = [str(PYTHON), 'control/weather/kalshi_market_reaction_ws.py']
for ticker in tickers:
    cmd.extend(['--ticker', ticker])
cmd.extend(['--duration-sec', '20'])

run = subprocess.run(
    cmd,
    cwd=ROOT,
    text=True,
    capture_output=True,
    timeout=50,
    env=os.environ.copy()
)

try:
    summary = json.loads(run.stdout.strip())
except Exception:
    summary = {}

log_value = summary.get('log')
if not log_value:
    result['status'] = 'BLOCKED_NO_LOG_PATH'
    result['ws_returncode'] = run.returncode
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(13)

log_path = Path(log_value)
if not log_path.is_file():
    result['status'] = 'BLOCKED_LOG_MISSING'
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(14)

delta_keys = set()
state_keys = set()

for raw in log_path.read_text(encoding='utf-8', errors='replace').splitlines():
    try:
        item = json.loads(raw)
    except Exception:
        continue

    kind = item.get('kind')
    if kind == 'ws_connected':
        result['ws_connected'] = True
    elif kind == 'capture_gap':
        result['capture_gaps'] += 1
    elif kind == 'capture_error':
        result['capture_errors'] += 1
    elif kind == 'trade':
        result['trade_frames'] += 1
    elif kind == 'market_state':
        result['market_state_events'] += 1
        ticker = item.get('ticker')
        seq = item.get('seq')
        if ticker is not None and isinstance(seq, int):
            state_keys.add((ticker, seq))
    elif kind == 'ws_raw':
        typ = item.get('type')
        msg = item.get('msg') or {}
        ticker = msg.get('market_ticker') if isinstance(msg, dict) else None
        seq = item.get('seq')
        if typ == 'orderbook_snapshot':
            result['snapshot_frames'] += 1
        elif typ == 'orderbook_delta':
            result['delta_frames'] += 1
            if ticker is not None and isinstance(seq, int):
                delta_keys.add((ticker, seq))

result['reconstructed_delta_states'] = len(delta_keys.intersection(state_keys))

if not result['ws_connected']:
    result['status'] = 'BLOCKED_WS_NOT_CONNECTED'
    code = 20
elif result['snapshot_frames'] < result['ticker_count']:
    result['status'] = 'BLOCKED_INCOMPLETE_SNAPSHOTS'
    code = 21
elif result['delta_frames'] == 0:
    result['status'] = 'PARTIAL_NO_DELTAS_OBSERVED'
    code = 22
elif result['reconstructed_delta_states'] != result['delta_frames']:
    result['status'] = 'BLOCKED_DELTA_RECONSTRUCTION_LOSS'
    code = 23
elif result['capture_gaps'] != 0 or result['capture_errors'] != 0:
    result['status'] = 'BLOCKED_CAPTURE_GAPS_OR_ERRORS'
    code = 24
else:
    result['status'] = 'PASS'
    code = 0

print(json.dumps(result, sort_keys=True))
raise SystemExit(code)
