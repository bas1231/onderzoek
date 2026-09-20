from pathlib import Path
from datetime import datetime,timezone
import json
import subprocess

root=Path.cwd()
task_id='EDGE-HUNTER-HOURLY-20260920T0500-E400'

for state in ['discovered','accepted','running','completed','failed']:
    p=root/'control/tasks'/state/(task_id+'.json')
    print('TASK_STATE',state,'EXISTS',p.exists())
    if p.exists():
        try:
            data=json.loads(p.read_text(encoding='utf-8'))
            print('TASK_STATE_STATUS',state,data.get('status'))
            print('TASK_STATE_STARTED',state,data.get('started_at'))
            print('TASK_STATE_FINISHED',state,data.get('finished_at'))
        except Exception as exc:
            print('TASK_STATE_READ_ERROR',state,str(exc))

run_dir=root/'knowledge/runs/edge_hunter'
run_files=list()
if run_dir.exists():
    run_files=[p for p in run_dir.iterdir() if p.is_file() and p.suffix=='.json']
    run_files.sort(key=lambda p:p.stat().st_mtime)
print('EDGE_HUNTER_RUN_FILE_COUNT',len(run_files))
for p in run_files[-8:]:
    print('RUN_FILE',p.name,'MTIME',datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat())
    try:
        data=json.loads(p.read_text(encoding='utf-8'))
        print('RUN_ID',data.get('run_id'))
        print('RUN_GENERATED_AT',data.get('generated_at'))
        print('RUN_STATUS',data.get('status'))
        print('RUN_REPORT',data.get('report'))
    except Exception as exc:
        print('RUN_READ_ERROR',str(exc))

check_dirs=[
    Path.home()/'.local/state/prediction-research/analysis/polymarket_fill_checkpoints',
    Path.home()/'.local/state/prediction-research/analysis/kwi_full_station_checkpoints'
]
for d in check_dirs:
    print('CHECKPOINT_DIR',d,'EXISTS',d.exists())
    files=list()
    if d.exists():
        files=[p for p in d.iterdir() if p.is_file()]
        files.sort(key=lambda p:p.stat().st_mtime)
    print('CHECKPOINT_COUNT',len(files))
    for p in files[-5:]:
        print('CHECKPOINT_FILE',p.name,'MTIME',datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat())

for unit in ['prediction-research-hourly-director.timer','prediction-research-hourly-director.service']:
    try:
        result=subprocess.run(['systemctl','--user','show',unit,'--property=ActiveState,SubState,LastTriggerUSec,ExecMainStartTimestamp,ExecMainExitTimestamp,ExecMainStatus'],capture_output=True,text=True,timeout=20,check=False)
        print('SYSTEMD_UNIT',unit,'RC',result.returncode)
        print(result.stdout.strip())
        if result.stderr.strip():
            print('SYSTEMD_STDERR',result.stderr.strip())
    except Exception as exc:
        print('SYSTEMD_ERROR',unit,str(exc))

print('HOURLY_0500_DIAG_E401_PASS')
