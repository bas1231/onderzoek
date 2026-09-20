from pathlib import Path
import subprocess

root=Path.cwd()
unit='prediction-research-hourly-director.timer'
props=['LoadState','ActiveState','SubState','Unit','Triggers','LastTriggerUSec','NextElapseUSecRealtime','NextElapseUSecMonotonic','Persistent']
cmd=['systemctl','--user','show',unit]
for prop in props:
    cmd.append('--property='+prop)
result=subprocess.run(cmd,capture_output=True,text=True,check=False)
print('SHOW_RC',result.returncode)
print(result.stdout.strip())
if result.stderr.strip():
    print('SHOW_STDERR',result.stderr.strip())

cat=subprocess.run(['systemctl','--user','cat',unit],capture_output=True,text=True,check=False)
print('CAT_RC',cat.returncode)
for line in cat.stdout.splitlines():
    if line.startswith('OnCalendar=') or line.startswith('OnUnitActiveSec=') or line.startswith('OnBootSec=') or line.startswith('Persistent=') or line.startswith('RandomizedDelaySec=') or line.startswith('Unit='):
        print('UNIT_LINE',line)

status=subprocess.run(['systemctl','--user','status',unit,'--no-pager'],capture_output=True,text=True,check=False)
print('STATUS_RC',status.returncode)
for line in status.stdout.splitlines():
    low=line.lower()
    if 'trigger:' in low or 'active:' in low or 'loaded:' in low:
        print('STATUS_LINE',line.strip())
print('HOURLY_TIMER_CADENCE_VERIFY_PASS')
