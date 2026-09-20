from pathlib import Path
import sys
import json

root = Path.cwd()
sys.path.insert(0, str(root / 'control/edge_hunter'))
from director import prepare

runs = sorted((root / 'knowledge/runs').glob('hourly-*.json'), key=lambda p: p.stat().st_mtime)
if not runs:
    raise SystemExit('no_hourly_runs')
run_id = runs[-1].stem
packet_path = prepare(run_id)
packet = json.loads(packet_path.read_text(encoding='utf-8'))

if packet.get('decision') != 'NO_PROVEN_EDGE':
    raise SystemExit('decision_not_fail_closed')
if packet.get('live_trading') or packet.get('paid_actions') or packet.get('wallet_actions'):
    raise SystemExit('packet_money_action_violation')
if len(packet.get('lanes', {})) != 8:
    raise SystemExit('lane_count_mismatch')

candidates = packet.get('candidates', [])
ids = {row.get('candidate_id') for row in candidates}
required = {'KWI-INCOMPLETE-TO-CANONICAL-V1', 'PAYOFF-IDENTITY-MINING-V1'}
if not required.issubset(ids):
    raise SystemExit('seeded_candidates_missing')
for row in candidates:
    if row.get('live_trading') or row.get('paid_actions') or row.get('wallet_actions'):
        raise SystemExit('candidate_money_action_violation')

print('EDGE_HUNTER_PACKET_SMOKE_PASS')
print('RUN_ID', run_id)
print('LANE_COUNT', len(packet['lanes']))
print('CANDIDATE_COUNT', len(candidates))
print('CANDIDATES', ','.join(sorted(ids)))
print('DECISION', packet['decision'])
