from pathlib import Path
import subprocess,json
ids=['BROWSER-RELOAD-E046','BROWSER-RELOAD-VERIFY-E047','RETRY-REGRESSION-E049','WATCHDOG-FOUNDATION-E051','RELIABILITY-AUDIT-E053A','RELIABILITY-VALIDATE-E053B','TRANSPORT-PING-E054','RELIABILITY-INSPECT-E055','POST-WAKE-AUDIT-E057','RELIABILITY-CONSOLIDATE-E058','DIFF-DIAG-E059','RELIABILITY-CONSOLIDATE-E060','AUTONOMOUS-FOUNDATION-E061','AUTONOMOUS-FOUNDATION-E062','EXECUTOR-BACKOFF-E063','TRANSPORT-HEALTH-E064','MISSING-E063-DIAG-E065','PREDISCOVER-INSPECT-E066','PREDISCOVER-CONTEXT-E067','PREDISCOVER-ANCHORS-E068','DISCOVER-ENQUEUE-DIAG-E069','PREDISCOVER-INCIDENT-E070','E065-ACCEPT-DIAG-E071','DUPLICATE-ACCEPT-FIX-E072','E072-STATUS-E073','POSTFIX-NORMAL-E074A','AUTONOMOUS-PICKUP-E075']
out={}
for tid in ids:
 hits=[]
 for root in [Path('control/tasks'),Path('control/results'),Path('control/lifecycle')]:
  if root.exists(): hits += [str(p) for p in root.rglob('*') if tid in p.name]
 g=subprocess.run(['git','log','--all','--oneline','--grep='+tid,'-5'],capture_output=True,text=True).stdout.splitlines()
 out[tid]={'hits':hits,'git':g,'found':bool(hits or g)}
print(json.dumps(out,indent=2))