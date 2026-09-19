from pathlib import Path
from datetime import datetime
import json,subprocess
agents=json.loads(Path('agents/registry.json').read_text())
sources=json.loads(Path('knowledge/sources/registry.json').read_text())
director=json.loads(Path('control/hourly/director_manifest.json').read_text())
checks={'roles':len(agents.get('roles',[]))==11,'free_only':all(x.get('cost_class')=='free_public' for x in sources.get('sources',[])),'sources':len(sources.get('sources',[]))>=11,'live_off':director.get('live_trading') is False,'paid_off':director.get('paid_actions') is False,'wallet_off':director.get('wallet_actions') is False,'null_valid':director.get('valid_null_result')=='NO_PROVEN_EDGE','active':director.get('status')=='ACTIVE'}
ok=all(checks.values())
now=datetime.now().astimezone();stamp=now.strftime('%Y%m%d_%H%M%S')
lines=['# Hourly Director Dry Run','',f'Timestamp: {now.isoformat()}','',f'Status: {"PASS" if ok else "FAIL"}','','## Gates']
for k,v in checks.items():lines.append('- '+k+': '+('PASS' if v else 'FAIL'))
lines+=['','## Research status','','NO_PROVEN_EDGE','', 'This dry run validates orchestration only; it does not claim market edge.']
p=Path('hourly-reports')/(stamp+'_dry-run.md');p.parent.mkdir(parents=True,exist_ok=True);p.write_text(chr(10).join(lines)+chr(10))
r=lambda a:subprocess.run(a,capture_output=True,text=True,check=False)
d=r(['git','diff','--check']);out={'ok':ok and d.returncode==0,'checks':checks,'report':str(p)}
if out['ok']:
 r(['git','add',str(p)]);c=r(['git','commit','-m','test(hourly): validate director dry run']);z=r(['git','push','origin','HEAD:main']);out['commit_rc']=c.returncode;out['push_rc']=z.returncode;out['head']=r(['git','log','-1','--oneline']).stdout.strip()
print(json.dumps(out,indent=2))