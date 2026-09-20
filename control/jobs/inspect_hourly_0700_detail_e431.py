from pathlib import Path
import json
import subprocess

root=Path.cwd()
run_dir=root/'knowledge/runs/edge_hunter'
run_path=run_dir/'edge-hunt-hourly-20260920T070000+0200.json'
if not run_path.exists():
    raise SystemExit('0700_run_missing')
run=json.loads(run_path.read_text(encoding='utf-8'))

print('RUN_FILE',run_path)
print('RUN_CREATED_AT',run.get('created_at'))
print('RUN_DECISION',run.get('decision'))
print('TOP_LEVEL_KEYS',sorted(run.keys()))

candidates=run.get('candidates') or tuple()
print('CANDIDATE_COUNT',len(candidates))
for candidate in candidates:
    if not isinstance(candidate,dict):
        continue
    cid=str(candidate.get('candidate_id') or candidate.get('id') or candidate.get('hypothesis_id') or '')
    print('CANDIDATE_BEGIN',cid)
    print(json.dumps(candidate,sort_keys=True)[:12000])
    print('CANDIDATE_END',cid)

for key,value in run.items():
    low=str(key).lower()
    if 'kwi' in low or 'weather' in low or 'fill' in low or 'maker' in low or 'monitor' in low or 'checkpoint' in low:
        print('RELEVANT_TOP_LEVEL',key,json.dumps(value,sort_keys=True)[:16000])

commands=[
    ['systemctl','--user','list-timers','--all','--no-pager'],
    ['systemctl','--user','list-units','--all','--type=service','--no-pager'],
    ['systemctl','--user','list-unit-files','--no-pager']
]
terms=['hourly','director','edge','hunter','prediction','research']
for command in commands:
    result=subprocess.run(command,capture_output=True,text=True)
    print('SYSTEMCTL_COMMAND',' '.join(command),'RC',result.returncode)
    for line in result.stdout.splitlines():
        low=line.lower()
        if any(term in low for term in terms):
            print('SYSTEMCTL_MATCH',line[:2000])
    if result.stderr:
        print('SYSTEMCTL_STDERR',result.stderr[:4000])

print('HOURLY_0700_DETAIL_E431_PASS')
