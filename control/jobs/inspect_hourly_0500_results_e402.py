from pathlib import Path
import json

root=Path.cwd()
run=root/'knowledge/runs/edge_hunter/edge-hunt-hourly-20260920T050000+0200.json'
if not run.exists():
    raise SystemExit('hourly_run_missing')
data=json.loads(run.read_text(encoding='utf-8'))
print('RUN_PATH',run)
print('RUN_KEYS',sorted(data.keys()))
for key in sorted(data.keys()):
    value=data.get(key)
    if isinstance(value,(str,int,float,bool)) or value is None:
        print('RUN_FIELD',key,repr(value))
    elif isinstance(value,list):
        print('RUN_LIST',key,'LEN',len(value))
        for index,item in enumerate(value[:30]):
            print('RUN_LIST_ITEM',key,index,repr(item)[:3000])
    elif isinstance(value,dict):
        print('RUN_DICT',key,'KEYS',sorted(value.keys()))
        for subkey in sorted(value.keys()):
            print('RUN_DICT_FIELD',key,subkey,repr(value.get(subkey))[:3000])

maker_dir=root/'knowledge/raw/market_data/polymarket_fill_checkpoints'
maker_files=list()
if maker_dir.exists():
    maker_files=[p for p in maker_dir.iterdir() if p.is_file() and p.suffix=='.json']
    maker_files.sort(key=lambda p:p.stat().st_mtime)
print('MAKER_CHECKPOINT_COUNT',len(maker_files))
for p in maker_files[-3:]:
    print('MAKER_CHECKPOINT',p.name)
    try:
        item=json.loads(p.read_text(encoding='utf-8'))
        print('MAKER_KEYS',sorted(item.keys()))
        for key in ['retrieved_at','credit_start_effective','event_id','markets']:
            print('MAKER_FIELD',key,repr(item.get(key))[:6000])
    except Exception as exc:
        print('MAKER_READ_ERROR',str(exc))

kwi_dir=Path.home()/'.local/state/prediction-research/analysis/kwi_full_station_checkpoints'
kwi_files=list()
if kwi_dir.exists():
    kwi_files=[p for p in kwi_dir.iterdir() if p.is_file() and p.suffix=='.json' and 'finalized' not in p.name]
    kwi_files.sort(key=lambda p:p.stat().st_mtime)
print('KWI_CHECKPOINT_COUNT',len(kwi_files))
if kwi_files:
    p=kwi_files[-1]
    print('KWI_LATEST',p.name)
    item=json.loads(p.read_text(encoding='utf-8'))
    print('KWI_KEYS',sorted(item.keys()))
    for key in ['generated_at','scorable_prospective_pairs','open_eligible_pairs','qualified_city_count','window_finished','survival_evaluable','survival_pass','overall','by_city']:
        print('KWI_FIELD',key,repr(item.get(key))[:6000])
print('HOURLY_0500_RESULT_INSPECT_PASS')
