from pathlib import Path
import json
import os
import subprocess

ROOT = Path.cwd()
ENV_FILE = Path.home() / '.config' / 'prediction-research' / 'kalshi_readonly.env'
PYTHON = ROOT / '.venv' / 'bin' / 'python'
TICKERS = [
    'KXTEMPMIAH-26SEP2112-T79.99',
    'KXTEMPMIAH-26SEP2112-T80.99',
    'KXTEMPMIAH-26SEP2112-T81.99',
    'KXTEMPMIAH-26SEP2112-T82.99',
    'KXTEMPMIAH-26SEP2112-T83.99',
    'KXTEMPMIAH-26SEP2112-T84.99',
    'KXTEMPMIAH-26SEP2112-T85.99',
    'KXTEMPMIAH-26SEP2112-T86.99',
    'KXTEMPMIAH-26SEP2112-T87.99',
    'KXTEMPMIAH-26SEP2112-T88.99'
]

result = {
    'task': 'EDGE-HUNTER-KWI-MIAMI-WS-CANARY-E401A11',
    'event_ticker': 'KXTEMPMIAH-26SEP2112',
    'ticker_count': len(TICKERS),
    'env_file_present': ENV_FILE.is_file(),
    'ws_connected': False,
    'snapshot_frames': 0,
    'delta_frames': 0,
    'trade_frames': 0,
    'market_state_events': 0,
    'capture_errors': 0,
    'capture_gaps': 0,
    'credential_values_printed': False,
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

cmd = [
    str(PYTHON),
    'control/weather/kalshi_market_reaction_ws.py'
]
for ticker in TICKERS:
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

log_path = None
try:
    summary = json.loads(run.stdout.strip())
    log_path = summary.get('log')
except Exception:
    summary = {}

if log_path and Path(log_path).is_file():
    for raw in Path(log_path).read_text(encoding='utf-8', errors='replace').splitlines():
        try:
            event = json.loads(raw)
        except Exception:
            continue
        kind = event.get('kind')
        if kind == 'ws_connected':
            result['ws_connected'] = True
        elif kind == 'market_state':
            result['market_state_events'] += 1
        elif kind == 'trade':
            result['trade_frames'] += 1
        elif kind == 'capture_error':
            result['capture_errors'] += 1
        elif kind == 'capture_gap':
            result['capture_gaps'] += 1
        elif kind == 'ws_raw':
            typ = event.get('type')
            if typ == 'orderbook_snapshot':
                result['snapshot_frames'] += 1
            elif typ == 'orderbook_delta':
                result['delta_frames'] += 1

if result['ws_connected'] and result['snapshot_frames'] > 0 and result['capture_errors'] == 0:
    result['status'] = 'PASS'
    code = 0
elif result['ws_connected']:
    result['status'] = 'PARTIAL_WS_CONNECTED_NO_CLEAN_SNAPSHOT'
    code = 14
else:
    result['status'] = 'BLOCKED_WS_NOT_CONNECTED'
    code = 13

print(json.dumps(result, sort_keys=True))
raise SystemExit(code)
