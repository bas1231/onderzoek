from pathlib import Path
import json
import subprocess

ROOT = Path(file).resolve().parents[2]
TASK = 'CONTROL-WORK-CADENCE-VERIFY-E008'


def read(path):
    try:
        return path.read_text(encoding='utf-8')
    except Exception as exc:
        return f'<UNAVAILABLE {type(exc).name}: {exc}>'


def run(args):
    p = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    return {'rc': p.returncode, 'stdout': p.stdout.strip(), 'stderr': p.stderr.strip()}

result = {
    'task_id': TASK,
    'result_json': read(ROOT / 'control/results' / TASK / 'RESULT.json'),
    'stdout': read(ROOT / 'control/results' / TASK / 'stdout.log'),
    'stderr': read(ROOT / 'control/results' / TASK / 'stderr.log'),
    'lifecycle': read(ROOT / 'control/lifecycle' / f'{TASK}.json'),
    'cadence_state': read(Path.home() / '.local/state/prediction-research/work_cadence.json'),
    'bridge_service': run(['systemctl','--user','is-active','prediction-research-browser-bridge.service']),
    'executor_service': run(['systemctl','--user','is-active','prediction-research-executor.service']),
    'git_status': run(['git','status','--porcelain=v1']),
    'git_divergence': run(['git','rev-list','--left-right','--count','origin/main...HEAD']),
    'live_trading': False,
    'paid_actions': False,
    'wallet_actions': False
}

print(json.dumps(result, indent=2, sort_keys=True))
