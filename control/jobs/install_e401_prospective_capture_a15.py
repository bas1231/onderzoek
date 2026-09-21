from pathlib import Path
import json
import shutil
import subprocess

root = Path.cwd()
home = Path.home()
user_units = home / '.config' / 'systemd' / 'user'
source_dir = root / 'control' / 'weather' / 'systemd'
env_file = home / '.config' / 'prediction-research' / 'kalshi_readonly.env'

result = {
    'task': 'EDGE-HUNTER-KWI-PROSPECTIVE-CAPTURE-E401A15',
    'env_present': env_file.is_file(),
    'preflight_pass': False,
    'service_installed': False,
    'service_active': False,
    'kwi_timer_active': False,
    'twc_timer_active': False,
    'live_trading': False,
    'paid_action': False,
    'wallet_action': False,
    'economic_conclusion': 'NO_PROVEN_EDGE'
}


def run(*args):
    return subprocess.run(args, cwd=root, text=True, capture_output=True)


if not env_file.is_file():
    result['status'] = 'BLOCKED_ENV_MISSING'
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(10)

preflight = run(str(root / '.venv' / 'bin' / 'python'), 'control/weather/e401_prospective_supervisor.py', '--once', '--discovery-only')
result['preflight_pass'] = preflight.returncode == 0
result['preflight_stdout_tail'] = preflight.stdout[-1200:]
if not result['preflight_pass']:
    result['status'] = 'BLOCKED_PREFLIGHT'
    result['preflight_stderr_tail'] = preflight.stderr[-1200:]
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(11)

user_units.mkdir(parents=True, exist_ok=True)
units = [
    'prediction-research-e401-prospective.service',
    'prediction-research-kalshi-weather-index-recorder.service',
    'prediction-research-kalshi-weather-index-recorder.timer',
    'prediction-research-twc-recorder.service',
    'prediction-research-twc-recorder.timer',
]
for name in units:
    src = source_dir / name
    if src.is_file():
        shutil.copy2(src, user_units / name)

reload_result = run('systemctl', '--user', 'daemon-reload')
if reload_result.returncode != 0:
    result['status'] = 'BLOCKED_DAEMON_RELOAD'
    result['detail'] = reload_result.stderr[-1000:]
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(12)

enable_kwi = run('systemctl', '--user', 'enable', '--now', 'prediction-research-kalshi-weather-index-recorder.timer')
enable_twc = run('systemctl', '--user', 'enable', '--now', 'prediction-research-twc-recorder.timer')
enable_e401 = run('systemctl', '--user', 'enable', '--now', 'prediction-research-e401-prospective.service')
result['service_installed'] = enable_e401.returncode == 0

active_e401 = run('systemctl', '--user', 'is-active', 'prediction-research-e401-prospective.service')
active_kwi = run('systemctl', '--user', 'is-active', 'prediction-research-kalshi-weather-index-recorder.timer')
active_twc = run('systemctl', '--user', 'is-active', 'prediction-research-twc-recorder.timer')
result['service_active'] = active_e401.stdout.strip() == 'active'
result['kwi_timer_active'] = active_kwi.stdout.strip() == 'active'
result['twc_timer_active'] = active_twc.stdout.strip() == 'active'

if result['service_active'] and result['kwi_timer_active'] and result['twc_timer_active']:
    result['status'] = 'PASS'
    code = 0
else:
    result['status'] = 'BLOCKED_SERVICE_NOT_ACTIVE'
    result['service_detail'] = enable_e401.stderr[-1000:]
    result['kwi_detail'] = enable_kwi.stderr[-1000:]
    result['twc_detail'] = enable_twc.stderr[-1000:]
    code = 13

print(json.dumps(result, sort_keys=True))
raise SystemExit(code)
