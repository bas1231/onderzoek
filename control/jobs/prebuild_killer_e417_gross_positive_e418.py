from pathlib import Path
from datetime import datetime,timezone
import json
import math

root=Path.cwd()
raw_dir=Path.home()/'.local/state/prediction-research/raw/polymarket_gamma_keyset'
manifest_dir=root/'knowledge/raw/market_data/polymarket_neg_risk_keyset_manifests'
screen_dir=root/'knowledge/raw/market_data/polymarket_negrisk_gross_screen'

target_ids=['656186','688065']

events=dict()
for suffix in ['-e405.json','-e413.json']:
    matches=[p for p in manifest_dir.iterdir() if p.is_file() and p.name.endswith(suffix)]
    matches.sort(key=lambda p:p.stat().st_mtime)
    if not matches:
        raise SystemExit('manifest_missing_'+suffix)
    manifest=json.loads(matches[-1].read_text(encoding='utf-8'))
    for page in manifest.get('pages') or tuple():
        if not isinstance(page,dict):
            continue
        sha=str(page.get('sha256') or '')
        p=raw_dir/(sha+'.json')
        if not p.exists():
            raise SystemExit('raw_page_missing_'+sha)
        data=json.loads(p.read_text(encoding='utf-8'))
        for event in data.get('events') or tuple():
            if not isinstance(event,dict):
                continue
            eid=str(event.get('id') or '')
            if eid in target_ids:
                events[eid]=event

for eid in target_ids:
    if eid not in events:
        raise SystemExit('target_event_missing_'+eid)

screens=[p for p in screen_dir.iterdir() if p.is_file() and p.name.endswith('-e417.json')]
screens.sort(key=lambda p:p.stat().st_mtime)
if not screens:
    raise SystemExit('e417_screen_missing')
screen=json.loads(screens[-1].read_text(encoding='utf-8'))
results=dict()
for row in screen.get('results') or tuple():
    if isinstance(row,dict):
        eid=str(row.get('event_id') or '')
        if eid in target_ids:
            results[eid]=row
for eid in target_ids:
    if eid not in results:
        raise SystemExit('e417_result_missing_'+eid)

print('SCREEN_SOURCE',screens[-1])
print('SCREEN_RETRIEVED_AT',screen.get('retrieved_at'))

summaries=list()
for eid in target_ids:
    event=events[eid]
    row=results[eid]
    markets=[m for m in event.get('markets') or tuple() if isinstance(m,dict) and m.get('negRisk') is True]
    print('EVENT_BEGIN',eid)
    print('TITLE',event.get('title'))
    print('DESCRIPTION',repr(str(event.get('description') or ''))[:16000])
    print('EVENT_END_DATE',event.get('endDate'))
    print('NEG_RISK',event.get('negRisk'))
    print('NEG_RISK_AUGMENTED',event.get('negRiskAugmented'))
    print('MARKET_COUNT',len(markets))
    print('SCREEN_ASK_SUM',row.get('ask_sum'))
    print('SCREEN_COMMON_SIZE',row.get('common_size'))
    print('SCREEN_GROSS_PER_SET',row.get('gross_per_set'))
    print('SCREEN_GROSS_TOTAL',row.get('gross_total_at_top'))

    fee_known=True
    all_no_other=True
    schedules=list()
    questions=list()
    for market in markets:
        fee=market.get('feeSchedule') or dict()
        schedule=dict(enabled=market.get('feesEnabled'),rate=fee.get('rate'),exponent=fee.get('exponent'),takerOnly=fee.get('takerOnly'))
        schedules.append(schedule)
        if market.get('negRiskOther') is True:
            all_no_other=False
        question=str(market.get('question') or '')
        group_item=str(market.get('groupItemTitle') or '')
        questions.append(dict(market_id=str(market.get('id') or ''),group_item=group_item,question=question,end_date=str(market.get('endDate') or ''),neg_risk_other=market.get('negRiskOther'),fee=schedule))
        print('MARKET',market.get('id'))
        print('GROUP_ITEM',group_item)
        print('QUESTION',question)
        print('MARKET_END_DATE',market.get('endDate'))
        print('NEG_RISK_OTHER',market.get('negRiskOther'))
        print('FEE_SCHEDULE',schedule)

    ask_by_market=dict()
    for item in row.get('asks') or tuple():
        if isinstance(item,dict):
            ask_by_market[str(item.get('market_id') or '')]=item

    common_size=float(row.get('common_size'))
    fee_total=0.0
    for market in markets:
        mid=str(market.get('id') or '')
        item=ask_by_market.get(mid)
        if item is None:
            fee_known=False
            continue
        price=float(item.get('price'))
        fee=market.get('feeSchedule') or dict()
        enabled=market.get('feesEnabled')
        try:
            rate=float(fee.get('rate'))
            exponent=float(fee.get('exponent'))
        except Exception:
            rate=None
            exponent=None
        if enabled is False:
            value=0.0
        elif enabled is True and rate is not None and exponent==1.0 and fee.get('takerOnly') is True:
            value=round(math.prod((common_size,rate,price,1.0-price)),5)
        else:
            value=None
            fee_known=False
        print('LEG_FEE',mid,'ASK',price,'SIZE',common_size,'FEE',value)
        if value is not None:
            fee_total+=value

    gross_total=float(row.get('gross_total_at_top'))
    net_total=None
    net_roi=None
    capital=None
    if fee_known:
        net_total=gross_total-fee_total
        capital=math.prod((float(row.get('ask_sum')),common_size))+fee_total
        if capital>0:
            net_roi=net_total/capital

    rule_text=str(event.get('description') or '').lower()
    coverage_terms=[]
    for token in ['less than','between','greater','at least','more than','below','above','or more','or less']:
        if token in rule_text:
            coverage_terms.append(token)

    print('ALL_NO_NEG_RISK_OTHER',all_no_other)
    print('FEE_KNOWN',fee_known)
    print('TAKER_FEES_TOTAL',fee_total if fee_known else None)
    print('NET_TOTAL',net_total)
    print('NET_ROI',net_roi)
    print('RULE_COVERAGE_TERMS',coverage_terms)
    summaries.append(dict(event_id=eid,title=event.get('title'),ask_sum=row.get('ask_sum'),common_size=row.get('common_size'),gross_total=gross_total,all_no_neg_risk_other=all_no_other,fee_known=fee_known,taker_fees_total=(fee_total if fee_known else None),net_total=net_total,net_roi=net_roi,description=str(event.get('description') or ''),markets=questions))
    print('EVENT_END',eid)

stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
outdir=root/'knowledge/raw/market_data/polymarket_negrisk_prebuild_killers'
outdir.mkdir(parents=True,exist_ok=True)
out=outdir/(stamp+'-e418.json')
payload=dict(retrieved_at=datetime.now(timezone.utc).isoformat(),source_screen=str(screens[-1].relative_to(root)),live_trading=False,paid_actions=False,wallet_actions=False,events=summaries)
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')

net_positive=sum(1 for row in summaries if row.get('net_total') is not None and float(row.get('net_total'))>0)
print('TARGET_COUNT',len(summaries))
print('NET_POSITIVE_COUNT',net_positive)
print('OUTPUT_PATH',out)
print('PREBUILD_KILLER_E418_PASS')
