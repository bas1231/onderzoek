"""Run only a specified local pytest scope; preserve command, time and output."""
from pathlib import Path
import datetime
import json
import os
import subprocess
import sys

root = Path(sys.argv[1]).absolute()
label = sys.argv[2]
assert label.replace('_', '').isalnum(), 'invalid evidence label'
evidence = Path('/home/leonh/prediction_research_prod/knowledge/codex_audit/remediation')
python = '/home/leonh/prediction_research_prod/.venv/bin/python'
cmd = [python, '-m', 'pytest', '-q', *sys.argv[3:], '--tb=short', '-o', 'cache_dir=/tmp/codex-remediation-pytest-cache']
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(root)+':'+str(root/'control/weather'))
with (evidence/(label+'.log')).open('w') as output:
    try:
        proc = subprocess.run(cmd, cwd=root, env=env, stdout=output, stderr=subprocess.STDOUT, timeout=240)
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        rc = 'TIMEOUT_240'
(evidence/(label+'.json')).write_text(json.dumps({'command':cmd,'cwd':str(root),'started_at':started,'ended_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':rc,'environment':{'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':env['PYTHONPATH']}},indent=2))
print('Exit:',rc)
print((evidence/(label+'.log')).read_text()[-9000:])
