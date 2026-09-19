from pathlib import Path
import subprocess,json
root=Path('.')
for d in ['agents','knowledge/sources','knowledge/documents','knowledge/claims','knowledge/mechanisms','knowledge/runs','knowledge/candidates','knowledge/source_changes','control/hourly','control/director','tests/research']:(root/d).mkdir(parents=True,exist_ok=True)
nl=chr(10)
policy=['# NO-COST EXECUTION POLICY','','Default: fail closed.','','Without explicit user approval for the specific action, this project MUST NOT use paid APIs, paid datasets, cloud/VPS spend, subscriptions, trading fees, live orders, wallet actions, crypto transfers or any other metered/spend action. Public/free web research and local computation are allowed. Live trading remains disabled.']
plan=['# Overnight autonomous build','','1. Reliability/control plane','2. Repository and knowledge schema','3. Source registry and provenance/dedupe','4. Role-based research agents','5. Pre-Build Killer / Chief Falsifier / Independent Reproducer','6. Hourly scheduler and chat wake-up','7. First research run and hourly report','8. Audit, negative evidence and coverage gaps','','Success does not require finding an edge. NO_PROVEN_EDGE is valid. Paid actions, live trading and wallet actions remain disabled.']
(root/'control/NO_COST_POLICY.md').write_text(nl.join(policy)+nl)
(root/'control/OVERNIGHT_BUILD_PLAN.md').write_text(nl.join(plan)+nl)
subprocess.run(['git','add','control/NO_COST_POLICY.md','control/OVERNIGHT_BUILD_PLAN.md'],capture_output=True,text=True)
c=subprocess.run(['git','commit','-m','build(control): establish no-cost autonomous research foundation'],capture_output=True,text=True)
p=subprocess.run(['git','push','origin','HEAD:main'],capture_output=True,text=True)
print(json.dumps({'commit_rc':c.returncode,'push_rc':p.returncode,'head':subprocess.run(['git','log','-1','--oneline'],capture_output=True,text=True).stdout.strip()},indent=2))