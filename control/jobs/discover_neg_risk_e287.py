from urllib.request import Request, urlopen
import json

agent = 'PredictionEdgeHunter/1.0'
url = 'https://gamma-api.polymarket.com/events/keyset?closed=false&limit=100'
req = Request(url, headers={'User-Agent': agent})
with urlopen(req, timeout=30) as r:
    raw = r.read()
    status = r.status

data = json.loads(raw)
events = data.get('events', [])
print('HTTP', status)
print('TOP_KEYS', ','.join(sorted(data.keys())))
print('EVENT_COUNT', len(events))

neg_events = 0
neg_markets = 0
for event in events:
    matched = []
    for market in event.get('markets', []):
        if market.get('negRisk') is True or market.get('neg_risk') is True:
            matched.append(market)
    event_neg = False
    for key,value in event.items():
        if 'risk' in key.lower() and value is True:
            event_neg = True
    if not matched and not event_neg:
        continue
    neg_events += 1
    neg_markets += len(matched)
    print('EVENT_ID', event.get('id'))
    print('EVENT_TITLE', str(event.get('title',''))[:220])
    print('TOTAL_MARKETS', len(event.get('markets', [])))
    print('NEG_MARKETS', len(matched))
    for market in matched[:20]:
        print('MARKET_ID', market.get('id'))
        print('QUESTION', str(market.get('question',''))[:220])
        print('OUTCOMES', market.get('outcomes'))
        print('CLOB_IDS', market.get('clobTokenIds'))
    print('---')

print('NEG_EVENTS', neg_events)
print('NEG_MARKETS_TOTAL', neg_markets)
print('NEG_RISK_DISCOVERY_PASS')
