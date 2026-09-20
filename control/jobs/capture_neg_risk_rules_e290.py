from pathlib import Path
from urllib.request import Request, urlopen
from datetime import datetime, timezone
import json

root = Path.cwd()
url = 'https://gamma-api.polymarket.com/events/48292'
req = Request(url, headers={'User-Agent':'PredictionEdgeHunter/1.0'})
with urlopen(req, timeout=30) as r:
    raw = r.read()
    status = r.status

event = json.loads(raw)
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
outdir = root / 'knowledge/raw/market_rules/polymarket'
outdir.mkdir(parents=True, exist_ok=True)
out = outdir / (stamp + 'event_48292.json')
out.write_bytes(raw)

print('HTTP', status)
print('EVENT_ID', event.get('id'))
print('TITLE', event.get('title'))
print('EVENT_KEYS', ','.join(sorted(event.keys())))
for key in sorted(event.keys()):
    low = key.lower()
    if 'risk' in low or 'rule' in low or 'resolution' in low or 'description' in low:
        print('EVENT_FIELD', key, str(event.get(key))[:4000])

markets = event.get('markets', [])
print('MARKET_COUNT', len(markets))
for market in markets:
    print('MARKET_ID', market.get('id'))
    print('QUESTION', market.get('question'))
    for key in sorted(market.keys()):
        low = key.lower()
        if 'risk' in low or 'rule' in low or 'resolution' in low or 'description' in low or 'end' in low:
            value = str(market.get(key)).replace(chr(10), ' ')
            print('FIELD', key, value[:5000])
    print('---')

print('PATH', out)
print('NEG_RISK_RULE_CAPTURE_PASS')
