from pathlib import Path
import hashlib
import json

root=Path.cwd()
rule_dir=root/'knowledge/raw/market_rules/polymarket'
ids=['197776','428957','548858']
events=dict()
for eid in ids:
    files=sorted(rule_dir.glob('*event-'+eid+'.json'),key=lambda p:p.stat().st_mtime)
    if not files:
        raise SystemExit('missing_event_'+eid)
    p=files[-1]
    events[eid]=json.loads(p.read_text(encoding='utf-8'))
    print('SOURCE',eid,p)

fields=['id','title','slug','description','resolutionSource','startDate','endDate','active','closed','negRisk','negRiskAugmented','negRiskMarketID']
for eid in ids:
    event=events[eid]
    print('EVENT_BEGIN',eid)
    for key in fields:
        value=event.get(key)
        if key=='description':
            text=str(value or '')
            print('EVENT_FIELD',key,'SHA256',hashlib.sha256(text.encode()).hexdigest())
            print('EVENT_DESCRIPTION_TEXT',repr(text)[:12000])
        else:
            print('EVENT_FIELD',key,repr(value)[:4000])
    markets=event.get('markets') or tuple()
    print('MARKET_COUNT',len(markets))
    for market in markets:
        if not isinstance(market,dict):
            continue
        print('MARKET_BEGIN',market.get('id'))
        for key in ['groupItemTitle','question','description','resolutionSource','startDate','endDate','umaEndDate','active','closed','negRisk','negRiskOther','conditionId','questionID','slug']:
            value=market.get(key)
            if key=='description':
                text=str(value or '')
                print('MARKET_FIELD',key,'SHA256',hashlib.sha256(text.encode()).hexdigest())
                print('MARKET_DESCRIPTION_TEXT',repr(text)[:12000])
            else:
                print('MARKET_FIELD',key,repr(value)[:4000])
        print('MARKET_END')
    print('EVENT_END',eid)

for left,right in [('197776','428957'),('197776','548858'),('428957','548858')]:
    a=events[left]
    b=events[right]
    print('PAIR',left,right)
    print('DESCRIPTION_EQUAL',str(a.get('description') or '')==str(b.get('description') or ''))
    print('RESOLUTION_SOURCE_EQUAL',str(a.get('resolutionSource') or '')==str(b.get('resolutionSource') or ''))
    print('EVENT_END_EQUAL',str(a.get('endDate') or '')==str(b.get('endDate') or ''))
    print('EVENT_START_EQUAL',str(a.get('startDate') or '')==str(b.get('startDate') or ''))

third=events['548858']
third_markets=third.get('markets') or tuple()
market_ends=sorted(set(str((m or dict()).get('endDate') or '') for m in third_markets if isinstance(m,dict)))
market_descriptions=sorted(set(str((m or dict()).get('description') or '') for m in third_markets if isinstance(m,dict)))
market_sources=sorted(set(str((m or dict()).get('resolutionSource') or '') for m in third_markets if isinstance(m,dict)))
print('THIRD_UNIQUE_MARKET_ENDS',market_ends)
print('THIRD_UNIQUE_MARKET_DESCRIPTION_COUNT',len(market_descriptions))
for text in market_descriptions:
    print('THIRD_MARKET_DESCRIPTION',repr(text)[:12000])
print('THIRD_UNIQUE_RESOLUTION_SOURCES',market_sources)
print('ANTHROPIC_RULE_HORIZON_COMPARE_E407_PASS')
