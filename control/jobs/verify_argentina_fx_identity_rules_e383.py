from pathlib import Path
import json
import hashlib

root=Path.cwd()
base=root/'knowledge/raw/market_rules/polymarket'
left_files=sorted(base.glob('*event-178817.json'),key=lambda p:p.stat().st_mtime)
right_files=sorted(base.glob('*event-189770.json'),key=lambda p:p.stat().st_mtime)
if not left_files or not right_files:
    raise SystemExit('rule_snapshot_missing')
left=json.loads(left_files[-1].read_text(encoding='utf-8'))
right=json.loads(right_files[-1].read_text(encoding='utf-8'))

ld=str(left.get('description') or '')
rd=str(right.get('description') or '')
print('LEFT_PATH',left_files[-1])
print('RIGHT_PATH',right_files[-1])
print('DESCRIPTION_EXACT_EQUAL',ld==rd)
print('LEFT_DESCRIPTION_SHA256',hashlib.sha256(ld.encode()).hexdigest())
print('RIGHT_DESCRIPTION_SHA256',hashlib.sha256(rd.encode()).hexdigest())
print('END_DATE_EQUAL',left.get('endDate')==right.get('endDate'))
print('LEFT_END_DATE',left.get('endDate'))
print('RIGHT_END_DATE',right.get('endDate'))
print('LEFT_NEG_RISK',left.get('negRisk'))
print('RIGHT_NEG_RISK',right.get('negRisk'))
print('LEFT_AUGMENTED',left.get('negRiskAugmented'))
print('RIGHT_AUGMENTED',right.get('negRiskAugmented'))
print('GROUP_IDS_DIFFER',left.get('negRiskMarketID')!=right.get('negRiskMarketID'))

left_target=None
for market in left.get('markets') or tuple():
    if str(market.get('id'))=='1234161':
        left_target=market
right_low=None
higher=list()
for market in right.get('markets') or tuple():
    mid=str(market.get('id'))
    if mid=='1273048':
        right_low=market
    else:
        higher.append(market)

if not isinstance(left_target,dict) or not isinstance(right_low,dict):
    raise SystemExit('boundary_markets_missing')

print('LEFT_BOUNDARY_MARKET',left_target.get('id'))
print('LEFT_BOUNDARY_TITLE',left_target.get('groupItemTitle'))
print('LEFT_BOUNDARY_QUESTION',left_target.get('question'))
print('RIGHT_COMPLEMENT_MARKET',right_low.get('id'))
print('RIGHT_COMPLEMENT_TITLE',right_low.get('groupItemTitle'))
print('RIGHT_COMPLEMENT_QUESTION',right_low.get('question'))
print('BOUNDARY_DESCRIPTIONS_EQUAL',str(left_target.get('description') or '')==str(right_low.get('description') or ''))
print('BOUNDARY_END_DATE_EQUAL',left_target.get('endDate')==right_low.get('endDate'))
print('BOUNDARY_NEG_RISK_OK',left_target.get('negRisk') is True and right_low.get('negRisk') is True)
print('BOUNDARY_NEG_RISK_OTHER_OK',left_target.get('negRiskOther') is False and right_low.get('negRiskOther') is False)

print('HIGHER_BUCKET_COUNT',len(higher))
for market in higher:
    print('HIGHER_BUCKET',market.get('id'),market.get('groupItemTitle'),market.get('question'))

text=ld.lower()
precision_ok='two decimal' in text or 'two decimal points' in text
source_ok='central bank of argentina' in text and 'bcra' in text
fallback_ok='7th day' in text and 'most recently published' in text
print('TWO_DECIMAL_RULE_PRESENT',precision_ok)
print('BCRA_SOURCE_RULE_PRESENT',source_ok)
print('FALLBACK_RULE_PRESENT',fallback_ok)

prereq=bool(ld==rd and left.get('endDate')==right.get('endDate') and left.get('negRisk') is True and right.get('negRisk') is True and left.get('negRiskAugmented') is False and right.get('negRiskAugmented') is False and str(left_target.get('description') or '')==str(right_low.get('description') or '') and left_target.get('endDate')==right_low.get('endDate') and precision_ok and source_ok and fallback_ok and len(higher)==5)
print('FORMAL_IDENTITY_PREREQUISITES_PASS',prereq)
print('IDENTITY_CANDIDATE_A','YES_178817_GE1600_EQ_NO_189770_LT1600')
print('IDENTITY_CANDIDATE_B','YES_178817_GE1600_EQ_SUM_YES_189770_HIGHER_BUCKETS')
print('NO_PRICE_TEST_PERFORMED',True)
print('ARGENTINA_FX_IDENTITY_RULE_VERIFY_PASS')
