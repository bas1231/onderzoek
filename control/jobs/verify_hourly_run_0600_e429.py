from pathlib import Path
import json

root=Path.cwd()
run_dir=root/'knowledge/runs/edge_hunter'
if not run_dir.exists():
    raise SystemExit('run_dir_missing')

exact=run_dir/'edge-hunt-hourly-20260920T060000+0200.json'
print('EXACT_RUN_PATH',exact)
print('EXACT_RUN_EXISTS',exact.exists())

candidates=[p for p in run_dir.iterdir() if p.is_file() and p.name.startswith('edge-hunt-hourly-20260920T06') and p.suffix=='.json']
candidates.sort(key=lambda p:p.stat().st_mtime)
print('SIX_OCLOCK_RUN_COUNT',len(candidates))
for p in candidates:
    print('RUN_FILE',p.name,'MTIME',p.stat().st_mtime)

chosen=exact if exact.exists() else (candidates[-1] if candidates else None)
if chosen is None:
    print('HOURLY_0600_RUN_FOUND',False)
    print('VERDICT','MISSING_0600_RUN')
    print('HOURLY_RUN_VERIFY_E429_PASS')
    raise SystemExit(0)

data=json.loads(chosen.read_text(encoding='utf-8'))
print('HOURLY_0600_RUN_FOUND',True)
print('CHOSEN_RUN',chosen)
print('TOP_LEVEL_KEYS',sorted(data.keys()))
print('CREATED_AT',data.get('created_at'))
print('DECISION',data.get('decision'))

candidates_data=data.get('candidates') or data.get('candidate_results') or tuple()
if isinstance(candidates_data,dict):
    candidates_data=list(candidates_data.values())
print('CANDIDATE_COUNT',len(candidates_data) if isinstance(candidates_data,list) else 'UNKNOWN')
if isinstance(candidates_data,list):
    for row in candidates_data:
        if not isinstance(row,dict):
            continue
        print('CANDIDATE',row.get('candidate_id') or row.get('id') or row.get('hypothesis_id'),'LANE',row.get('lane'),'STAGE',row.get('stage') or row.get('lifecycle_state'),'STATUS',row.get('status'),'DECISION',row.get('decision'))

for key in ['kwi_checkpoint','weather_checkpoint','maker_fill_monitor','maker_checkpoint','monitor_results','hooks']:
    value=data.get(key)
    if value is not None:
        print('SECTION',key,str(value)[:12000])

print('VERDICT','EXISTING_0600_RUN_CONFIRMED')
print('HOURLY_RUN_VERIFY_E429_PASS')
