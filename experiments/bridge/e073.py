from pathlib import Path;import json;tid='DUPLICATE-ACCEPT-FIX-E072';hits=[]
for r in [Path('control/tasks'),Path('control/results'),Path('control/lifecycle')]: hits += [str(p) for p in r.rglob('*') if tid in p.name]
print(json.dumps({'task':tid,'hits':hits},indent=2))