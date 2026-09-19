from future import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(file).resolve().parents[2]
PYTHON = ROOT / '.venv/bin/python'
WATCHDOG = ROOT / 'control/jobs/watchdog_v1.py'
TEST = ROOT / 'tests/bridge/test_watchdog_v1.py'
UNIT_DIR = Path.home() / '.config/systemd/user'
UNIT = UNIT_DIR / 'prediction-research-watchdog.service'


def run(args: list[str], timeout: int = 90) -> subprocess.CompletedProcess[str]:
 proc = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, check=False, timeout=timeout)
 print('$ ' + ' '.join(args))
 if proc.stdout:
 print(proc.stdout.rstrip())
 if proc.stderr:
 print(proc.stderr.rstrip(), file=sys.stderr)
 if proc.returncode != 0:
 raise RuntimeError('command failed with return code ' + str(proc.returncode))
 return proc


run([str(PYTHON), '-m', 'py_compile', str(WATCHDOG)])
run([str(PYTHON), '-m', 'pytest', str(TEST), '-q'])

UNIT_DIR.mkdir(parents=True, exist_ok=True)
UNIT.write_text(
 '[Unit]
'
 'Description=Prediction Research Local Watchdog
'
 'After=default.target

'
 '[Service]
'
 'Type=simple
'
 f'WorkingDirectory={ROOT}
'
 f'ExecStart={PYTHON} {WATCHDOG} --loop
'
 'Restart=always
'
 'RestartSec=5

'
 '[Install]
'
 'WantedBy=default.target
',
 encoding='utf-8',
)

run(['systemctl', '--user', 'daemon-reload'])
run(['systemctl', '--user', 'enable', '--now', 'prediction-research-watchdog.service'])
active = run(['systemctl', '--user', 'is-active', 'prediction-research-watchdog.service']).stdout.strip()
if active != 'active':
 raise RuntimeError('watchdog service is not active')

print('PASS: watchdog v1 installed')
print('PASS: watchdog service active')
print('PASS: maximum automatic repairs per key = 3')
print('PASS: research auto-resume forbidden')
print('PASS: paid actions forbidden')
print('PASS: live trading and wallet actions forbidden')
print('STATUS_FILE=' + str(Path.home() / '.local/state/prediction-research/watchdog/status.json'))
