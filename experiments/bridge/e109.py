from pathlib import Path
import importlib.util,json,subprocess
ROOT=Path.cwd()
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
sweepmod=load('source_sweep',ROOT/'control/hourly/source_sweep.py')
path,data=sweepmod.sweep(max_workers=4)
run=lambda a:subprocess.run(a,capture_output=True,text=True,check=False)
d=run(['git','diff','--check'])
out={'ok':d.returncode==0,'sweep':str(path.relative_to(ROOT)),'source_count':data['source_count'],'success_count':data['success_count'],'failure_count':data['failure_count'],'results':data['results']}
if out['ok']:
 run(['git','add','knowledge/documents/manifests','knowledge/runs/source_sweeps']);c=run(['git','commit','-m','run(hourly): archive first multi-source sweep']);p=run(['git','push','origin','HEAD:main']);out['commit_rc']=c.returncode;out['push_rc']=p.returncode;out['head']=run(['git','log','-1','--oneline']).stdout.strip()
print(json.dumps(out,indent=2))