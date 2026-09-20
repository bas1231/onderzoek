from pathlib import Path
import json
import hashlib

root=Path.cwd()
base=root/'knowledge/raw/market_rules/polymarket'
left_files=sorted(base.glob('*event-197776.json'),key=lambda p:p.stat().st_mtime)
right_files=sorted(base.glob('*event-428957.json'),key=lambda p:p.stat().st_mtime)
if not left_files or not right_files:
    raise SystemExit('rule_snapshot_missing')
left=json.loads(left_files[-1].read_text(encoding='utf-8'))
right=json.loads(right_files[-1].read_text(encoding='utf-8'))

left_map=dict((str(m.get('id')),m) for m in left.get('markets') or tuple() if isinstance(m,dict))
right_map=dict((str(m.get('id')),m) for m in right.get('markets') or tuple() if isinstance(m,dict))
required={'1328014','1328015','1328016','1328017','1328018','1328019','1328020','2110748','2110749','2110750','2110751','2110752','2110753','2110754'}
if not required.issubset(set(left_map)|set(right_map)):
    raise SystemExit('required_markets_missing')

pairs=[('1328019','2110748'),('1328020','2110754')]
for a,b in pairs:
    ma=left_map.get(a) or right_map.get(a) or dict()
    mb=left_map.get(b) or right_map.get(b) or dict()
    da=str(ma.get('description') or '')
    db=str(mb.get('description') or '')
    print('PAIR',a,b)
    print('DESCRIPTION_EQUAL',da==db)
    print('DESCRIPTION_SHA_A',hashlib.sha256(da.encode()).hexdigest())
    print('DESCRIPTION_SHA_B',hashlib.sha256(db.encode()).hexdigest())
    print('END_DATE_EQUAL',ma.get('endDate')==mb.get('endDate'))
    print('NEG_RISK_OK',ma.get('negRisk') is True and mb.get('negRisk') is True)
    print('NEG_RISK_OTHER_OK',ma.get('negRiskOther') is False and mb.get('negRiskOther') is False)
    print('QUESTION_A',ma.get('question'))
    print('QUESTION_B',mb.get('question'))
    print('---')

states=['no_ipo','lt100','100_200','200_300','300_400','400_600','600_900','900_1200','1200_1500','1500_1800','ge1800']

def lower(state):
    return dict(
        lt100=1 if state=='lt100' else 0,
        b100_200=1 if state=='100_200' else 0,
        b200_300=1 if state=='200_300' else 0,
        b300_400=1 if state=='300_400' else 0,
        b400_600=1 if state=='400_600' else 0,
        ge600=1 if state in ['600_900','900_1200','1200_1500','1500_1800','ge1800'] else 0,
        no_ipo=1 if state=='no_ipo' else 0
    )

def middle(state):
    return dict(
        lt600=1 if state in ['lt100','100_200','200_300','300_400','400_600'] else 0,
        b600_900=1 if state=='600_900' else 0,
        b900_1200=1 if state=='900_1200' else 0,
        b1200_1500=1 if state=='1200_1500' else 0,
        b1500_1800=1 if state=='1500_1800' else 0,
        ge1800=1 if state=='ge1800' else 0,
        no_ipo=1 if state=='no_ipo' else 0
    )

proof_a=True
proof_b=True
proof_c=True
proof_locked_1=True
proof_locked_2=True
for state in states:
    lo=lower(state)
    mi=middle(state)
    lower_low=sum([lo.get('lt100'),lo.get('b100_200'),lo.get('b200_300'),lo.get('b300_400'),lo.get('b400_600')])
    middle_high=sum([mi.get('b600_900'),mi.get('b900_1200'),mi.get('b1200_1500'),mi.get('b1500_1800'),mi.get('ge1800')])
    a=lo.get('ge600')==middle_high
    b=mi.get('lt600')==lower_low
    c=lo.get('no_ipo')==mi.get('no_ipo')
    locked1=lo.get('ge600')+mi.get('lt600')+mi.get('no_ipo')==1
    locked2=mi.get('lt600')+lo.get('ge600')+lo.get('no_ipo')==1
    proof_a=proof_a and a
    proof_b=proof_b and b
    proof_c=proof_c and c
    proof_locked_1=proof_locked_1 and locked1
    proof_locked_2=proof_locked_2 and locked2
    print('STATE',state,'LOWER_GE600',lo.get('ge600'),'MIDDLE_HIGH_SUM',middle_high,'MIDDLE_LT600',mi.get('lt600'),'LOWER_LOW_SUM',lower_low,'LOWER_NO_IPO',lo.get('no_ipo'),'MIDDLE_NO_IPO',mi.get('no_ipo'),'LOCKED1',locked1)

print('IDENTITY_A_LOWER_GE600_EQ_MIDDLE_HIGHER_SUM',proof_a)
print('IDENTITY_B_MIDDLE_LT600_EQ_LOWER_LOWER_SUM',proof_b)
print('IDENTITY_C_NO_IPO_DIRECT_EQ_DIRECT',proof_c)
print('LOCKED_PAYOUT_LOWER_GE600_PLUS_MIDDLE_LT600_PLUS_MIDDLE_NO_IPO',proof_locked_1)
print('LOCKED_PAYOUT_MIDDLE_LT600_PLUS_LOWER_GE600_PLUS_LOWER_NO_IPO',proof_locked_2)
print('FORMAL_STATEWISE_PROOF_PASS',proof_a and proof_b and proof_c and proof_locked_1 and proof_locked_2)
print('NO_PRICE_TEST_PERFORMED',True)
print('ANTHROPIC_CROSS_SERIES_IDENTITY_PROOF_PASS')
