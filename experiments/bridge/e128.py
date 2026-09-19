from pathlib import Path
import json
R=Path.cwd()
tid='LOCAL-HOURLY-SAFE-E127'
hits=[]
for b in [R/'control/tasks',R/'control/results',R/'control/lifecycle']:
 if b.exists():
  hits += [str(p.relative_to(R)) for p in b.rglob('*') if tid in p.name]
out={'e127_hits':hits,'hourly_cycle_exists':(R/'control/hourly/hourly_cycle.py').exists()}
print(json.dumps(out,indent=2))