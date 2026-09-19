from pathlib import Path
import importlib.util,json,subprocess
ROOT=Path.cwd()
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
mod=load('apply_sweep',ROOT/'control/hourly/apply_sweep.py')
run_path,report,sweep=mod.apply()
run=json.loads(run_path.read_text())
r=lambda a:subprocess.run(a,capture_output=True,text=True,check=False)
d=r(['git','diff','--check'])
out={'ok':d.returncode==0,'run_id':run['run_id'],'success_count':sweep['success_count'],'failure_count':sweep['failure_count'],'source_provenance_gate':run['gates'].get('source_provenance'),'report':str(report.relative_to(ROOT)),'run_manifest':str(run_path.relative_to(ROOT))}
if out['ok']:
 r(['git','add',str(run_path),str(report)]);c=r(['git','commit','-m','run(hourly): apply first source sweep to director']);p=r(['git','push','origin','HEAD:main']);out['commit_rc']=c.returncode;out['push_rc']=p.returncode
print(json.dumps(out,indent=2))