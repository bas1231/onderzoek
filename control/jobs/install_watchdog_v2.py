from future import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(file).resolve().parents[2]
PYTHON = ROOT / '.venv/bin/python'
WATCHDOG = ROOT / 'control/jobs/watchdog_v1.py'
TEST = ROOT / 'tests/bridge/test_watchdog_v1.py'
UNIT_DIR = Path.home() / '.config/systemd/user'
UNIT = UNIT_DIR / 'prediction-research-watchdog.service'
STATUS = Path.home() / '.local/state/prediction-research/watchdog/status.json'
NL = chr(10)


def run(args: list[str], timeout: int = 90) -> subprocess.CompletedProcess[str]:
 proc = subprocess.run(
 args,
 cwd=ROOT,
 capture_output=True,
 text=True,
 check=False,
 timeout=timeout,
 )
 print('$ ' + ' '.join(args))
 if proc.stdout:
 print(proc.stdout.rstrip())
 if proc.stderr:
 print(proc.stderr.rstrip(), file=sys.stderr)
 if proc.returncode != 0:
 raise RuntimeError('command failed with return code ' + str(proc.returncode))
 return proc


run([str(PYTHON), '-m', 'py_compile', str(WATCHDOG)])
run([str(PYTHON), '-m', 'py_compile', str(Path(file).resolve())])
run([str(PYTHON), '-m', 'pytest', str(TEST), '-q'])

UNIT_DIR.mkdir(parents=True, exist_ok=True)
unit_lines = [
 '[Unit]',
 'Description=Prediction Research Local Watchdog',
 'After=default.target',
 '',
 '[Service]',
 'Type=simple',
 'WorkingDirectory=' + str(ROOT),
 'ExecStart=' + str(PYTHON) + ' ' + str(WATCHDOG) + ' --loop',
 'Restart=always',
 'RestartSec=5',
 '',
 '[Install]',
 'WantedBy=default.target',
 '',
]
UNIT.write_text(NL.join(unit_lines), encoding='utf-8')

run(['systemctl', '--user', 'daemon-reload'])
run(['systemctl', '--user', 'enable', '--now', 'prediction-research-watchdog.service'])
active = run(['systemctl', '--user', 'is-active', 'prediction-research-watchdog.service']).stdout.strip()
if active != 'active':
 raise RuntimeError('watchdog service is not active')

for _ in range(10):
 if STATUS.exists():
 break
 time.sleep(1)

if not STATUS.exists():
 raise RuntimeError('watchdog status file was not created')

status = json.loads(STATUS.read_text(encoding='utf-8'))
guardrails = status.get('guardrails', {})

required_false = [
 'research_auto_resume_allowed',
 'paid_actions_allowed',
 'live_trading_allowed',
 'wallet_actions_allowed',
 'running_task_kill_allowed',
]

for key in required_false:
 if guardrails.get(key) is not False:
 raise RuntimeError('guardrail validation failed: ' + key)

if guardrails.get('max_repairs_per_key') != 3:
 raise RuntimeError('repair-budget validation failed')

print('PASS: watchdog v1 installed')
print('PASS: watchdog service active')
print('PASS: status file created')
print('PASS: no paid actions allowed')
print('PASS: no research auto-resume allowed')
print('PASS: no live trading or wallet actions allowed')
print('PASS: no running-task kill allowed')
print('PASS: max automatic repairs per key = 3')
print('WATCHDOG_STATUS=' + str(status.get('status')))
print('QUEUE_STATUS=' + str(status.get('queue_status')))
print('ISSUE_COUNT=' + str(len(status.get('issues', []))))
print('STATUS_FILE=' + str(STATUS))
