from pathlib import Path
import json
import subprocess

root = Path.cwd()
rows = []
for path in sorted((root / 'knowledge/candidates').glob('*.json')):
    row = json.loads(path.read_text(encoding='utf-8'))
    rows.append({
        'candidate_id': row.get('candidate_id', path.stem),
        'lane': row.get('lane', 'UNKNOWN'),
        'phase': row.get('phase', 'UNKNOWN'),
        'decision': row.get('decision', 'UNPROVEN'),
        'live_trading': bool(row.get('live_trading', False)),
        'paid_actions': bool(row.get('paid_actions', False)),
        'wallet_actions': bool(row.get('wallet_actions', False))
    })
if len(rows) < 2:
    raise SystemExit('candidate_count_below_expected')
for row in rows:
    if row['live_trading'] or row['paid_actions'] or row['wallet_actions']:
        raise SystemExit('fail_closed_violation')
print(json.dumps(rows, indent=2, sort_keys=True))
subprocess.run(['git','add','control/jobs/edge_candidate_summary.py'], cwd=root, check=True)
diff = subprocess.run(['git','diff','--cached','--quiet'], cwd=root)
if diff.returncode != 0:
    subprocess.run(['git','commit','-m','add simple edge candidate summary'], cwd=root, check=True)
    subprocess.run(['git','push'], cwd=root, check=True)
print('EDGE_CANDIDATE_SUMMARY_PASS')
