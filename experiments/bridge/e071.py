from pathlib import Path
import json
p=Path('control/lifecycle/SCANNER-RECOVERY-E065.json')
print('=== LIFECYCLE ===')
print(p.read_text() if p.exists() else 'MISSING')
print('=== PENDING ===')
q=Path('control/tasks/pending/SCANNER-RECOVERY-E065.json')
print(q.read_text() if q.exists() else 'MISSING')
print('=== BRIDGE FUNCTIONS ===')
lines=Path('control/browser_bridge.py').read_text().splitlines()
for name in ['def discover(', 'def enqueue(']:
 i=next((i for i,l in enumerate(lines) if name in l),None)
 if i is not None:
  for n in range(i,min(i+95,len(lines))): print(f'{n+1}: {lines[n]}')