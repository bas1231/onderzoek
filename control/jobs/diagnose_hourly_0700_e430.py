from pathlib import Path
from datetime import datetime,timezone
import json
import subprocess

root=Path.cwd()
run_dir=root/'knowledge/runs/edge_hunter'
print('RUN_DIR_EXISTS',run_dir.exists())

matches=list()
if run_dir.exists():
    for p in run_dir.iterdir():
        if p.is_file() and '20260920T070000+0200' in p.name:
            matches.append(p)
    matches.sort(key=lambda p:p.stat().st_mtime)

print('EXACT_0700_RUN_COUNT',len(matches))
for p in matches:
    print('RUN_FILE',p)
    try:
        data=json.loads(p.read_text(encoding='utf-8'))
    except Exception as exc:
        print('RUN_PARSE_ERROR',str(exc))
        continue
    print('RUN_DECISION',data.get('decision'))
    print('RUN_CREATED_AT',data.get('created_at'))
    candidates=data.get('candidates') or tuple()
    print('RUN_CANDIDATE_COUNT',len(candidates) if isinstance(candidates,list) else None)
    if isinstance(candidates,list):
        for row in candidates:
            if not isinstance(row,dict):
                continue
            print('CANDIDATE',row.get('candidate_id') or row.get('id'),'LANE',row.get('lane'),'STAGE',row.get('stage'),'STATUS',row.get('status'))

recent=list()
if run_dir.exists():
    for p in run_dir.iterdir():
        if p.is_file():
            recent.append(p)
    recent.sort(key=lambda p:p.stat().st_mtime,reverse=True)
print('RECENT_RUN_FILES')
for p in recent[:8]:
    print('RECENT',p.name,datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat())

services=['edge-hunter-hourly.timer','edge-hunter-hourly.service']
for unit in services:
    result=subprocess.run(['systemctl','--user','status',unit,'--no-pager'],capture_output=True,text=True)
    print('SYSTEMCTL_BEGIN',unit,'RC',result.returncode)
    for line in result.stdout.splitlines()[:40]:
        print('SYSTEMCTL',line[:1600])
    for line in result.stderr.splitlines()[:20]:
        print('SYSTEMCTL_ERR',line[:1600])
    print('SYSTEMCTL_END',unit)

print('HOURLY_0700_DIAGNOSIS_E430_PASS')
