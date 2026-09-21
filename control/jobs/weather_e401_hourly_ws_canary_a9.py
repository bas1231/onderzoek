from pathlib import Path
import json
import os
import subprocess
import sys

ROOT = Path.cwd()
ENV_FILE = Path.home() / '.config' / 'prediction-research' / 'kalshi_readonly.env'
PYTHON = ROOT / '.venv' / 'bin' / 'python'

result = {
    'task': 'EDGE-HUNTER-KWI-MARKET-WS-CANARY-E401A9',
    'env_file_present': ENV_FILE.is_file(),
    'preflight_pass': False,
    'series': {},
    'selected_ticker': None,
    'ws_connected': False,
    'capture_errors': 0,
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

pre = subprocess.run(
    [str(PYTHON), 'control/jobs/preflight_kwi_market_reaction_e401.py'],
    cwd=ROOT,
    text=True,
    capture_output=True
)

try:
    preflight = json.loads(pre.stdout.strip())
except Exception:
    preflight = {}

required = [
    'api_key_id_present',
    'private_key_path_present',
    'private_key_file_exists',
    'websockets_available',
    'cryptography_available'
]
result['preflight_pass'] = pre.returncode == 0 and all(preflight.get(k) is True for k in required)

if not result['preflight_pass']:
    result['status'] = 'BLOCKED_PREFLIGHT'
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(11)

sys.path.insert(0, str(ROOT / 'control' / 'weather'))
import kalshi_market_reaction_recorder as recorder

series_list = ['KXTEMPNYCH', 'KXTEMPLAXH', 'KXTEMPCHIH']
all_tickers = []

for series in series_list:
    try:
        tickers = recorder.discover(series)
        result['series'][series] = {
            'count': len(tickers),
            'tickers': tickers[:30]
        }
        all_tickers.extend(tickers)
    except Exception as exc:
        result['series'][series] = {
            'count': 0,
            'error_type': type(exc).name
        }

all_tickers = sorted(set(all_tickers))
if not all_tickers:
    result['status'] = 'BLOCKED_NO_OPEN_HOURLY_MARKETS'
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(12)

selected = all_tickers[0]
result['selected_ticker'] = selected

ws = subprocess.run(
    [
        str(PYTHON),
        'control/weather/kalshi_market_reaction_ws.py',
        '--ticker', selected,
        '--duration-sec', '15'
    ],
    cwd=ROOT,
    text=True,
    capture_output=True,
    timeout=45,
    env=os.environ.copy()
)

log_path = None
try:
    ws_summary = json.loads(ws.stdout.strip())
    log_path = ws_summary.get('log')
except Exception:
    ws_summary = {}

if log_path and Path(log_path).is_file():
    for raw in Path(log_path).read_text(encoding='utf-8', errors='replace').splitlines():
        try:
            event = json.loads(raw)
        except Exception:
            continue
        if event.get('kind') == 'ws_connected':
            result['ws_connected'] = True
        if event.get('kind') in {'capture_error', 'capture_gap'}:
            result['capture_errors'] += 1

result['status'] = 'PASS' if result['ws_connected'] else 'BLOCKED_WS_NOT_CONNECTED'
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if result['ws_connected'] else 13)
