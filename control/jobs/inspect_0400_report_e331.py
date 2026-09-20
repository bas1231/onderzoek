from pathlib import Path
import json

root=Path.cwd()
p=root/'knowledge/runs/edge_hunter/edge-hunt-hourly-20260920T040000+0200.json'
if not p.exists():
    raise SystemExit('run_missing')
data=json.loads(p.read_text(encoding='utf-8'))
print('RUN_ID',data.get('run_id'))
print('DECISION',data.get('decision'))
print('STATUS',data.get('status'))
print('GENERATED_AT',data.get('generated_at'))
print('LANE_COUNT',len(data.get('lanes') or tuple()))
print('CANDIDATE_COUNT',len(data.get('candidates') or tuple()))
print('SOURCE_SUCCESS',data.get('source_success'))
print('SOURCE_FAILURE',data.get('source_failure'))
print('REPORT_STATUS',data.get('report_status'))
print('REPORT_DECISION',data.get('report_decision'))
for gate in data.get('gates') or tuple():
    if isinstance(gate,dict):
        print('GATE',gate.get('name'),gate.get('status'))
for cand in data.get('candidates') or tuple():
    if isinstance(cand,dict):
        print('CANDIDATE',cand.get('candidate_id'),cand.get('lane'),cand.get('lifecycle_phase'),cand.get('status'),cand.get('decision'))
print('REPORT_PATH',p)
print('HOURLY_0400_REPORT_INSPECTION_PASS')
