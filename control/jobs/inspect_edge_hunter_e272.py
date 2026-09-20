from pathlib import Path
import json

root = Path.cwd()
run_id = 'hourly-20260920T030000+0200'
packet_path = root / 'knowledge/runs/edge_hunter' / ('edge-hunt-' + run_id + '.json')
run_path = root / 'knowledge/runs' / (run_id + '.json')
report_path = root / 'hourly-reports' / (run_id + '.md')

packet = json.loads(packet_path.read_text(encoding='utf-8'))
print('DECISION', packet.get('decision'))
print('LANE_COUNT', len(packet.get('lanes', {})))
print('CANDIDATES')
for row in packet.get('candidates', []):
    print(row.get('candidate_id'), row.get('lane'), row.get('phase'), row.get('decision'))
print('LANES')
for name,row in sorted(packet.get('lanes', {}).items()):
    print(name, 'evidence', row.get('evidence_count'), 'gaps', len(row.get('coverage_gaps', [])), 'next', row.get('next_action'))
    for gap in row.get('coverage_gaps', []):
        print('GAP', name, gap)
if run_path.exists():
    run = json.loads(run_path.read_text(encoding='utf-8'))
    print('SOURCE_SUCCESS', run.get('source_success_count'))
    print('SOURCE_FAILURE', run.get('source_failure_count'))
    print('GATES', json.dumps(run.get('gates', {}), sort_keys=True))
if report_path.exists():
    print('REPORT')
    print(report_path.read_text(encoding='utf-8')[:12000])
