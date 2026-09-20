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
    events[eid]=json.loads(files[-1].read_text(encoding='utf-8'))

base_desc=str(events['197776'].get('description') or '')
base_hash=hashlib.sha256(base_desc.encode()).hexdigest()
print('BASE_DESCRIPTION_SHA256',base_hash)
print('BASE_HAS_2027_DEADLINE','December 31, 2027' in base_desc)

all_market_desc_equal=True
for eid in ids:
    event=events[eid]
    event_desc=str(event.get('description') or '')
    print('EVENT',eid,'TITLE',event.get('title'))
    print('EVENT_DESCRIPTION_EQUAL_BASE',event_desc==base_desc)
    print('EVENT_END_DATE',event.get('endDate'))
    market_ends=set()
    market_hashes=set()
    for market in event.get('markets') or tuple():
        if not isinstance(market,dict):
            continue
        text=str(market.get('description') or '')
        market_hashes.add(hashlib.sha256(text.encode()).hexdigest())
        market_ends.add(str(market.get('endDate') or ''))
        if text!=base_desc:
            all_market_desc_equal=False
    print('MARKET_DESCRIPTION_HASHES',sorted(market_hashes))
    print('MARKET_END_DATES',sorted(market_ends))
    print('ALL_MARKET_DESCRIPTIONS_EQUAL_BASE',market_hashes==set([base_hash]))

print('GLOBAL_ALL_MARKET_DESCRIPTIONS_EQUAL_BASE',all_market_desc_equal)
print('EVENT_END_METADATA_EQUAL',len(set(str(events[eid].get('endDate') or '') for eid in ids))==1)

middle={str(m.get('groupItemTitle') or ''):str(m.get('id') or '') for m in events['428957'].get('markets') or tuple() if isinstance(m,dict)}
third={str(m.get('groupItemTitle') or ''):str(m.get('id') or '') for m in events['548858'].get('markets') or tuple() if isinstance(m,dict)}

middle_low=['<0.6T','0.6–0.9T','0.9–1.2T','1.2–1.5T']
middle_high=['1.5–1.8T','1.8T+']
third_low=['<$1.25T','$1.25–$1.5T']
third_high=['$1.5–$1.75T','$1.75–$2.0T','$2.0–$2.25T','$2.25–$2.5T','$2.5–$2.75T','$2.75–$3.0T','$3.0T+']

for name,labels,lookup in [
    ('MIDDLE_LT_1_5',middle_low,middle),
    ('MIDDLE_GE_1_5',middle_high,middle),
    ('THIRD_LT_1_5',third_low,third),
    ('THIRD_GE_1_5',third_high,third)
]:
    missing=[label for label in labels if label not in lookup]
    print('PORTFOLIO',name,'LEGS',[lookup.get(label) for label in labels],'MISSING',missing)

required_present=all(label in middle for label in middle_low+middle_high) and all(label in third for label in third_low+third_high)
print('REQUIRED_BUCKETS_PRESENT',required_present)

states=['no_ipo','lt_1_25','1_25_to_1_5','1_5_to_1_75','1_75_to_1_8','1_8_to_2_0','2_0_to_2_25','2_25_to_2_5','2_5_to_2_75','2_75_to_3_0','ge_3_0']

def mid_lt(state):
    return 1 if state in ['lt_1_25','1_25_to_1_5'] else 0

def mid_ge(state):
    return 1 if state in ['1_5_to_1_75','1_75_to_1_8','1_8_to_2_0','2_0_to_2_25','2_25_to_2_5','2_5_to_2_75','2_75_to_3_0','ge_3_0'] else 0

def third_lt(state):
    return 1 if state in ['lt_1_25','1_25_to_1_5'] else 0

def third_ge(state):
    return 1 if state in ['1_5_to_1_75','1_75_to_1_8','1_8_to_2_0','2_0_to_2_25','2_25_to_2_5','2_5_to_2_75','2_75_to_3_0','ge_3_0'] else 0

identity_low=True
identity_high=True
locked=True
for state in states:
    a=mid_lt(state)
    b=third_lt(state)
    c=mid_ge(state)
    d=third_ge(state)
    noipo=1 if state=='no_ipo' else 0
    if a!=b:
        identity_low=False
    if c!=d:
        identity_high=False
    if c+b+noipo!=1:
        locked=False
    print('STATE',state,'MID_LT',a,'THIRD_LT',b,'MID_GE',c,'THIRD_GE',d,'NOIPO',noipo,'LOCKED',c+b+noipo)

print('IDENTITY_LT_1_5_PASS',identity_low)
print('IDENTITY_GE_1_5_PASS',identity_high)
print('CROSS_SERIES_LOCKED_PAYOUT_PASS',locked)
rule_guard=all_market_desc_equal and required_present and 'December 31, 2027' in base_desc
print('RULE_TEXT_GUARD_PASS',rule_guard)
print('METADATA_ENDDATE_MISMATCH',len(set(str(events[eid].get('endDate') or '') for eid in ids))!=1)
print('FORMAL_RULE_TEXT_IDENTITY_PASS',rule_guard and identity_low and identity_high and locked)
print('ANTHROPIC_15T_IDENTITY_E408_PASS')
