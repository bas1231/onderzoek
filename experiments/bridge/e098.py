from pathlib import Path
import json
ids=['PUBLIC-COLLECTOR-E095','BRIDGE-HEALTH-E097']
out={}
for tid in ids:
 hits=[]
 for root in [Path('control/tasks'),Path('control/results'),Path('control/lifecycle')]:
  if root.exists(): hits += [str(p) for p in root.rglob('*') if tid in p.name]
 out[tid]=hits
print(json.dumps(out,indent=2))