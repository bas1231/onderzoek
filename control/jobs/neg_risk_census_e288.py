from urllib.request import Request, urlopen
import json

agent = 'PredictionEdgeHunter/1.0'
base = 'https://gamma-api.polymarket.com/events/keyset?closed=false&limit=100'
cursor = None
rows = []
total = 0

for page in range(5):
    url = base
    if cursor:
        url = url + '&cursor=' + cursor
    req = Request(url, headers={'User-Agent': agent})
    with urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    events = data.get('events', [])
    total += len(events)
    for event in events:
        markets = event.get('markets', [])
        neg = []
        other = 0
        for market in markets:
            if market.get('negRisk') is True or market.get('neg_risk') is True:
                neg.append(market)
                if market.get('negRiskOther') is True or market.get('neg_risk_other') is True:
                    other += 1
        if neg:
            rows.append({'event_id': str(event.get('id')), 'title': str(event.get('title','')), 'market_count': len(markets), 'neg_count': len(neg), 'other_count': other})
    cursor = data.get('next_cursor')
    if not cursor:
        break

print('EVENTS_SCANNED', total)
print('NEG_RISK_EVENTS', len(rows))
if rows:
    sizes = [r['neg_count'] for r in rows]
    print('MIN_NEG_MARKETS', min(sizes))
    print('MAX_NEG_MARKETS', max(sizes))
    print('WITH_OTHER_FLAG', sum(1 for r in rows if r['other_count'] > 0))

eligible = [r for r in rows if r['neg_count'] >= 3 and r['neg_count'] <= 40]
print('ELIGIBLE_SMALL_GROUPS', len(eligible))
for row in sorted(eligible, key=lambda x: (x['neg_count'], x['event_id']))[:20]:
    print('EVENT', row['event_id'], 'NEG', row['neg_count'], 'OTHER', row['other_count'])
    print('TITLE', row['title'][:220])

print('NEG_RISK_CENSUS_PASS')
