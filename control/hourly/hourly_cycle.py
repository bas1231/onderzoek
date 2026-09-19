from pathlib import Path
import importlib.util
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

subprocess.run(
    [str(R / '.venv/bin/python'), str(R / 'control/hourly/hourly_wake.py')],
    check=False,
)

print(run['run_id'], sweep_data['success_count'], sweep_data['failure_count'])
