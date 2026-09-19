from pathlib import Path
import importlib.util
import json
import subprocess

R = Path(__file__).resolve().parents[2]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

runner = load('agent_runner', R / 'control/hourly/agent_runner.py')
sweep = load('source_sweep', R / 'control/hourly/source_sweep.py')
apply_sweep = load('apply_sweep', R / 'control/hourly/apply_sweep.py')
extractor = load('extract_text', R / 'control/hourly/extract_text.py')
quality = load('source_quality', R / 'control/hourly/source_quality.py')
router = load('role_router', R / 'control/hourly/role_router.py')

run, manifest, report, packets = runner.create_packets()
sweep_path, sweep_data = sweep.sweep(max_workers=4)
apply_sweep.apply()

for item in sweep_data['results']:
    if not item.get('ok'):
        continue
    try:
        extractor.extract(item['source_id'])
    except Exception:
        pass

quality_data, quality_path = quality.grade(run['run_id'])
routing = router.route(run['run_id'])
routing_path = R / 'knowledge/runs' / (run['run_id'] + '-routing.json')
routing_path.write_text(json.dumps(routing, indent=2, sort_keys=True) + chr(10))

run_path = R / 'knowledge/runs' / (run['run_id'] + '.json')
current = json.loads(run_path.read_text())
current['source_quality'] = {
    'usable_count': quality_data.get('usable_count'),
    'low_text_yield_count': quality_data.get('low_text_yield_count'),
    'ref': str(quality_path.relative_to(R)),
}
current['automated_routing'] = {
    role: len(data.get('evidence', []))
    for role, data in routing.items()
}
current['routing_ref'] = str(routing_path.relative_to(R))
run_path.write_text(json.dumps(current, indent=2, sort_keys=True) + chr(10))

report_path = R / 'hourly-reports' / (run['run_id'] + '.md')
marker = '## Automated preparation'
existing = report_path.read_text(errors='replace') if report_path.exists() else ''
if marker not in existing:
    with report_path.open('a') as handle:
        handle.write(chr(10) + marker + chr(10) + chr(10))
        handle.write('Usable sources: ' + str(quality_data.get('usable_count')) + chr(10))
        handle.write('Low-text-yield sources: ' + str(quality_data.get('low_text_yield_count')) + chr(10))
        for role, data in routing.items():
            handle.write('- ' + role + ': ' + str(len(data.get('evidence', []))) + ' routed evidence items' + chr(10))

subprocess.run(
    [str(R / '.venv/bin/python'), str(R / 'control/hourly/hourly_wake.py')],
    check=False,
)

print(
    run['run_id'],
    sweep_data['success_count'],
    sweep_data['failure_count'],
    quality_data.get('usable_count'),
)
