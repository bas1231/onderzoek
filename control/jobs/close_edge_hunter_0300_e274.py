from pathlib import Path
import json
import subprocess

root = Path.cwd()
run_id = 'hourly-20260920T030000+0200'
run_path = root / 'knowledge/runs' / (run_id + '.json')
report_path = root / 'hourly-reports' / (run_id + '.md')

run = json.loads(run_path.read_text(encoding='utf-8'))
run['status'] = 'COMPLETED'
run['candidate_status'] = 'UNPROVEN'
run['decision'] = 'NO_PROVEN_EDGE'
run['gates']['source_provenance'] = 'PASS'
run['gates']['point_in_time'] = 'PARTIAL'
run['gates']['signal_edge'] = 'NOT_TESTED'
run['gates']['market_edge'] = 'NOT_TESTED'
run['gates']['execution_reality'] = 'NOT_TESTED'
run['gates']['falsification'] = 'NOT_TESTED'
run['gates']['reproduction'] = 'NOT_TESTED'
run_path.write_text(json.dumps(run, indent=2, sort_keys=True) + chr(10), encoding='utf-8')

lines = [
    '# Hourly Research Report',
    '',
    'Run: ' + run_id,
    '',
    '## Status',
    'COMPLETED',
    '',
    '## Semantic review',
    'No new execution-realistic edge was established in this cycle.',
    'Routed algebra and microstructure evidence was generic venue documentation rather than evidence of mispricing.',
    'Behavioral and informed-flow lanes produced no substantive evidence.',
    'Settlement and weather evidence mainly reconfirmed already-known source and settlement mechanics.',
    '',
    '## Candidates',
    'KWI-INCOMPLETE-TO-CANONICAL-V1 remains DISCOVERED and UNPROVEN.',
    'PAYOFF-IDENTITY-MINING-V1 remains DISCOVERED and UNPROVEN.',
    '',
    '## Negative evidence',
    'Generic documentation matches for combo and order book are insufficient to support an edge claim.',
    'Changed source content did not produce a new falsifiable market-edge candidate in this cycle.',
    '',
    '## Coverage gaps',
    'No live executable orderbook snapshot source is present in the hourly registry.',
    'Venue-specific contract rule pages require deeper retrieval than documentation landing pages.',
    'No point-in-time participant identity or flow dataset is available for informed-flow testing.',
    'No TWC-specific primary source is present in the generic hourly registry.',
    'Aviationweather retrieval failed in this cycle.',
    '',
    '## Gates',
    'Source provenance: PASS',
    'Point in time: PARTIAL',
    'Signal edge: NOT_TESTED',
    'Market edge: NOT_TESTED',
    'Execution reality: NOT_TESTED',
    'Falsification: NOT_TESTED',
    'Reproduction: NOT_TESTED',
    '',
    '## Decision',
    'NO_PROVEN_EDGE',
    '',
    '## Next hour',
    'Prioritize market-level evidence over landing-page evidence.',
    'Add free read-only executable L2 capture and deeper venue-specific rule retrieval.',
    'Continue the two seeded candidates only under their predefined falsification gates.',
    'Search all eight lanes for new mechanisms without promoting narrative plausibility to evidence.',
    ''
]
report_path.write_text(chr(10).join(lines), encoding='utf-8')

subprocess.run(['git','add',str(run_path.relative_to(root)),str(report_path.relative_to(root))], cwd=root, check=True)
subprocess.run(['git','commit','--only',str(run_path.relative_to(root)),str(report_path.relative_to(root)),'-m','close 0300 edge hunter semantic review'], cwd=root, check=True)
subprocess.run(['git','push'], cwd=root, check=True)

print('EDGE_HUNTER_0300_CLOSED')
print('STATUS', run['status'])
print('DECISION', run['decision'])
print('POINT_IN_TIME', run['gates']['point_in_time'])
