from pathlib import Path;import json,subprocess;tid='EXECUTOR-BACKOFF-E063';hits=[]
for root in [Path('control/tasks'),Path('control/results'),Path('control/lifecycle')]:
 hits += [str(p) for p in root.rglob('*') if tid in p.name]
r=subprocess.run(['git','log','--all','--oneline','--grep='+tid,'-10'],capture_output=True,text=True)
print(json.dumps({'hits':hits,'git':r.stdout.splitlines()},indent=2))