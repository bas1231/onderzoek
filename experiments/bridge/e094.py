import json,subprocess
from pathlib import Path
r=subprocess.run(['.venv/bin/python','control/hourly/run_manifest.py'],capture_output=True,text=True)
out={'rc':r.returncode,'stdout':r.stdout.strip(),'stderr':r.stderr.strip()}
if r.returncode==0:
 d=json.loads(r.stdout);p=Path(d['path']);m=json.loads(p.read_text());out['checks']={'agents':len(m['agents'])==11,'sources':len(m['sources'])>=11,'all_agents_pending':all(v=='PENDING' for v in m['agents'].values()),'all_sources_pending':all(v=='PENDING' for v in m['sources'].values()),'decision':m['decision']=='NO_PROVEN_EDGE','live_off':m['live_trading'] is False,'paid_off':m['paid_actions'] is False,'wallet_off':m['wallet_actions'] is False};out['ok']=all(out['checks'].values());subprocess.run(['git','add',str(p)]);c=subprocess.run(['git','commit','-m','test(hourly): validate immutable run manifest'],capture_output=True,text=True);z=subprocess.run(['git','push','origin','HEAD:main'],capture_output=True,text=True);out['commit_rc']=c.returncode;out['push_rc']=z.returncode
print(json.dumps(out,indent=2))