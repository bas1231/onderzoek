from pathlib import Path
import importlib.util,json,subprocess
ROOT=Path.cwd()
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
collector=load('collector',ROOT/'control/hourly/collector.py')
change=load('change',ROOT/'control/hourly/change_detection.py')
sources={s['id']:s for s in collector.load_sources()}
source=sources['kalshi_docs']
body,headers,status=collector.fetch(source)
manifest=collector.archive(source,body,headers,status)
classification=change.classify('kalshi_docs')
run=lambda a:subprocess.run(a,capture_output=True,text=True,check=False)
d=run(['git','diff','--check'])
out={'ok':status==200 and len(body)>0 and d.returncode==0,'source':'kalshi_docs','bytes':len(body),'http_status':status,'sha256':manifest['sha256'],'is_new_content':manifest['is_new_content'],'classification':classification}
if out['ok']:
 run(['git','add','knowledge/documents/manifests/kalshi_docs']);c=run(['git','commit','-m','test(hourly): archive first primary source']);p=run(['git','push','origin','HEAD:main']);out['commit_rc']=c.returncode;out['push_rc']=p.returncode;out['head']=run(['git','log','-1','--oneline']).stdout.strip()
print(json.dumps(out,indent=2))