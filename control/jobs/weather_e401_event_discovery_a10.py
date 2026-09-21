from pathlib import Path
import json
import urllib.parse
import urllib.request

BASE = 'https://external-api.kalshi.com/trade-api/v2'
SERIES = ['KXTEMPNYCH', 'KXTEMPCHIH', 'KXTEMPLAXH', 'KXTEMPMIAH']

result = {
    'task': 'EDGE-HUNTER-KWI-EVENT-DISCOVERY-E401A10',
    'series': {},
    'selected_ticker': None,
    'live_trading': False,
    'paid_action': False,
    'wallet_action': False,
    'economic_conclusion': 'NO_PROVEN_EDGE'
}


def get_json(path, params):
    query = urllib.parse.urlencode(params)
    req = urllib.request.Request(
        BASE + path + '?' + query,
        headers={'User-Agent': 'PredictionResearch-KWI-discovery/1'},
        method='GET'
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode('utf-8'))


all_tickers = []

for series in SERIES:
    row = {}
    for status in ['open', 'unopened']:
        try:
            data = get_json('/events', {
                'series_ticker': series,
                'status': status,
                'limit': 200,
                'with_nested_markets': 'true'
            })
            events = data.get('events', [])
            event_rows = []
            for event in events:
                markets = event.get('markets') or []
                tickers = [m.get('ticker') for m in markets if m.get('ticker')]
                all_tickers.extend(tickers)
                event_rows.append({
                    'event_ticker': event.get('event_ticker'),
                    'market_count': len(tickers),
                    'market_tickers': tickers[:20]
                })
            row[status] = {
                'event_count': len(events),
                'events': event_rows[:20]
            }
        except Exception as exc:
            row[status] = {
                'event_count': 0,
                'error_type': type(exc).name,
                'error': str(exc)[:200]
            }
    result['series'][series] = row

all_tickers = sorted(set(all_tickers))
if all_tickers:
    result['selected_ticker'] = all_tickers[0]
    result['status'] = 'PASS'
else:
    result['status'] = 'BLOCKED_NO_NESTED_MARKETS'

print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if all_tickers else 12)
