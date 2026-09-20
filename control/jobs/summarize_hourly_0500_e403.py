from pathlib import Path
import json

root=Path.cwd()
run=root/'knowledge/runs/edge_hunter/edge-hunt-hourly-20260920T050000+0200.json'
if not run.exists():
    raise SystemExit('run_missing')
data=json.loads(run.read_text(encoding='utf-8'))
print('RUN_ID',data.get('run_id'))
print('CREATED_AT',data.get('created_at'))
print('DECISION',data.get('decision'))
print('CANDIDATE_COUNT',len(data.get('candidates') or tuple()))
for row in data.get('candidates') or tuple():
    if not isinstance(row,dict):
        continue
    print('CANDIDATE',row.get('candidate_id'),'LANE',row.get('lane'),'PHASE',row.get('phase'),'DECISION',row.get('decision'))
    if row.get('candidate_id')=='ASSET-RANK-MAKER-HEDGE-V1':
        monitor=row.get('prospective_monitoring') or dict()
        print('MAKER_MONITOR',repr(monitor)[:4000])
    if row.get('candidate_id')=='KWI-FULL-STATION-PRECANONICAL-V1':
        print('KWI_PROTOCOLS',repr(row.get('prospective_protocols')))

maker_candidates=[
    root/'knowledge/raw/market_data/polymarket_fill_checkpoints',
    root/'knowledge/raw/market_data/polymarket_fill_checkpoints',
    Path.home()/'.local/state/prediction-research/analysis/polymarket_fill_checkpoints'
]
seen=set()
maker_files=list()
for d in maker_candidates:
    if str(d) in seen:
        continue
    seen.add(str(d))
    print('MAKER_DIR',d,'EXISTS',d.exists())
    if not d.exists():
        continue
    for p in d.iterdir():
        if p.is_file() and p.suffix=='.json':
            maker_files.append(p)
maker_files.sort(key=lambda p:p.stat().st_mtime)
print('MAKER_CHECKPOINT_COUNT',len(maker_files))
if maker_files:
    p=maker_files[-1]
    print('MAKER_LATEST',p)
    item=json.loads(p.read_text(encoding='utf-8'))
    print('MAKER_KEYS',sorted(item.keys()))
    markets=item.get('markets') or tuple()
    print('MAKER_MARKET_COUNT',len(markets))
    for market in markets:
        if not isinstance(market,dict):
            continue
        print('MAKER_MARKET',market.get('market_id'),'SHADOW_BID',market.get('shadow_bid'),'INITIAL_QUEUE',market.get('initial_queue_ahead'),'QUALIFYING_SIZE',market.get('qualifying_executed_size'),'REQUIRED_SIZE',market.get('required_executed_size'),'FULL_FILL',market.get('full_fill'))
    for key in ['retrieved_at','credit_start_effective','upper_credit_epoch','window_finished','full_fill_count']:
        print('MAKER_FIELD',key,item.get(key))

kwi_dir=Path.home()/'.local/state/prediction-research/analysis/kwi_full_station_checkpoints'
kwi_files=list()
if kwi_dir.exists():
    kwi_files=[p for p in kwi_dir.iterdir() if p.is_file() and p.suffix=='.json' and 'finalized' not in p.name]
    kwi_files.sort(key=lambda p:p.stat().st_mtime)
print('KWI_CHECKPOINT_COUNT',len(kwi_files))
if kwi_files:
    p=kwi_files[-1]
    print('KWI_LATEST',p)
    item=json.loads(p.read_text(encoding='utf-8'))
    print('KWI_SCORABLE',item.get('scorable_prospective_pairs'))
    print('KWI_OPEN',item.get('open_eligible_pairs'))
    print('KWI_QUALIFIED_CITY_COUNT',item.get('qualified_city_count'))
    print('KWI_WINDOW_FINISHED',item.get('window_finished'))
    print('KWI_SURVIVAL_EVALUABLE',item.get('survival_evaluable'))
    print('KWI_SURVIVAL_PASS',item.get('survival_pass'))
    overall=item.get('overall') or dict()
    print('KWI_OVERALL_N',overall.get('n'))
    print('KWI_PRIMARY_MAE',overall.get('primary_mae'))
    print('KWI_BASELINE_MAE',overall.get('baseline_mae'))
    print('KWI_PRIMARY_RMSE',overall.get('primary_rmse'))
    print('KWI_BASELINE_RMSE',overall.get('baseline_rmse'))
    for city,metrics in (item.get('by_city') or dict()).items():
        print('KWI_CITY',city,'N',metrics.get('n'),'PRIMARY_MAE',metrics.get('primary_mae'),'BASELINE_MAE',metrics.get('baseline_mae'),'LEAD_MEAN',metrics.get('lead_seconds_mean'))
print('HOURLY_0500_SUMMARY_E403_PASS')
