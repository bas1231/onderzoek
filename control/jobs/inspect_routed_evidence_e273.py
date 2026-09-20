from pathlib import Path
import json

root = Path.cwd()
run = 'hourly-20260920T030000+0200'
p = root / 'knowledge/runs' / (run + '-routing.json')
data = json.loads(p.read_text(encoding='utf-8'))

for role,row in sorted(data.items()):
    print('ROLE', role, 'STATUS', row.get('status'))
    for gap in row.get('coverage_gaps', []):
        print('GAP', gap)
    for item in row.get('evidence', []):
        print('SOURCE', item.get('source_id'))
        print('STATE', item.get('source_state'))
        print('TERM', item.get('term'))
        snippet = item.get('snippet', '').replace(chr(10), ' ')
        print('SNIPPET', snippet[:1800])
        print('---')
