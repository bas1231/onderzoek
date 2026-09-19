from pathlib import Path
import subprocess,json
run=lambda a:subprocess.run(a,capture_output=True,text=True,check=False)
p=Path('control/browser_extension/background.js'); p.write_text(p.read_text().rstrip()+chr(10))
targets=['.gitignore','control/browser_bridge.py','control/browser_extension/background.js','control/browser_extension/content.js','control/browser_extension/manifest.json','control/executor.py','control/jobs/lifecycle_supervisor.py']
checks={'diff':run(['git','diff','--check']).returncode==0,'bridge':run(['python3','-m','py_compile','control/browser_bridge.py']).returncode==0,'executor':run(['python3','-m','py_compile','control/executor.py']).returncode==0,'supervisor':run(['python3','-m','py_compile','control/jobs/lifecycle_supervisor.py']).returncode==0,'background':run(['node','--check','control/browser_extension/background.js']).returncode==0,'content':run(['node','--check','control/browser_extension/content.js']).returncode==0}
ok=all(checks.values()); out={'checks':checks,'ok':ok}
if ok:
 run(['git','add','--',*targets]); c=run(['git','commit','-m','fix(control): consolidate no-silent-waiting reliability stack']); out['commit_rc']=c.returncode; out['commit']=c.stdout.strip(); psh=run(['git','push','origin','HEAD:main']); out['push_rc']=psh.returncode; out['head']=run(['git','log','-1','--oneline']).stdout.strip(); out['status']=run(['git','status','--short']).stdout.splitlines()
print(json.dumps(out,indent=2))