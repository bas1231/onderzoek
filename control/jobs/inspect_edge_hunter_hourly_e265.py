from pathlib import Path
import subprocess

root = Path.cwd()
files = [
    root / 'control/hourly/edge_hunter_cycle.py',
    root / 'control/edge_hunter/director.py',
    Path.home() / '.config/systemd/user/prediction-research-hourly-director.service'
]
for path in files:
    print('FILE', path)
    if not path.exists():
        print('MISSING')
        continue
    print(path.read_text(encoding='utf-8', errors='replace')[:12000])
    print('END_FILE')
status = subprocess.run(['systemctl','--user','is-active','prediction-research-hourly-director.timer'], capture_output=True, text=True)
print('TIMER_ACTIVE', status.stdout.strip())
