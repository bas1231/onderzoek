from pathlib import Path
import json
R=Path.cwd()
out=[]
for p in (R/'control/browser_extension').glob('*.js'):
 t=p.read_text(errors='replace')
 hits=[]
 for k in ['/ack','ACKED','ack','outbox']:
  if k in t: hits.append(k)
 out.append({'file':str(p.relative_to(R)),'hits':hits,'bytes':len(t)})
print(json.dumps(out,indent=2))