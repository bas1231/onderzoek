from pathlib import Path
import json,subprocess
ids=['SCANNER-RECOVERY-E065','PREDISCOVER-ANCHORS-E068']
out={}
for tid in ids:
 hits=[]
 for root in [Path('control/tasks'),Path('control/results'),Path('control/lifecycle')]:
  hits += [str(p) for p in root.rglob('*') if tid in p.name]
 out[tid]=hits
j=subprocess.run(['journalctl','--user','-u','prediction-research-browser-bridge.service','--since','15 minutes ago','--no-pager'],capture_output=True,text=True).stdout
out['bridge_tail']=[l for l in j.splitlines() if '/discover' in l or '/enqueue' in l][-80:]
print(json.dumps(out,indent=2))