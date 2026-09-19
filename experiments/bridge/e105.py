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
r=lambda a:subprocess.run(a,capture_output=True,text=True,check=False)
out={'ok':status==200 and classification.get('status') in {'UNCHANGED','CHANGED'},'http_status':status,'sha256':manifest['sha256'],'is_new_content':manifest['is_new_content'],'classification':classification}
if out['ok']:
 r(['git','add','knowledge/documents/manifests/kalshi_docs']);c=r(['git','commit','-m','test(hourly): prove source dedupe']);p=r(['git','push','origin','HEAD:main']);out['commit_rc']=c.returncode;out['push_rc']=p.returncode
print(json.dumps(out,indent=2))