from pathlib import Path
from datetime import datetime,timezone
import importlib.util,json,subprocess
ROOT=Path.cwd()
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
extractor=load('extract_text',ROOT/'control/hourly/extract_text.py')
registry=json.loads((ROOT/'knowledge/sources/registry.json').read_text())
rows=[]
for source in registry['sources']:
 sid=source['id']
 try:
  out,data=extractor.extract(sid)
  rows.append({'source_id':sid,'ok':True,'document_sha256':data['document_sha256'],'retrieved_at':data['retrieved_at'],'chars':data['chars'],'text_ref':str(out.relative_to(ROOT)),'manifest_ref':data['manifest_ref']})
 except Exception as exc:
  rows.append({'source_id':sid,'ok':False,'error':type(exc).__name__+': '+str(exc)[:300]})
run_id='corpus-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
index=ROOT/'knowledge/runs'/(run_id+'.json')
index.write_text(json.dumps({'run_id':run_id,'created_at':datetime.now(timezone.utc).isoformat(),'success_count':sum(1 for r in rows if r['ok']),'failure_count':sum(1 for r in rows if not r['ok']),'documents':rows},indent=2,sort_keys=True)+chr(10))
r=lambda a:subprocess.run(a,capture_output=True,text=True,check=False)
d=r(['git','diff','--check'])
out={'ok':d.returncode==0,'run_id':run_id,'success_count':sum(1 for r in rows if r['ok']),'failure_count':sum(1 for r in rows if not r['ok']),'documents':[{'source_id':x['source_id'],'ok':x['ok'],'chars':x.get('chars')} for x in rows]}
if out['ok']:
 r(['git','add','knowledge/documents/text',str(index)]);c=r(['git','commit','-m','run(research): extract first source corpus']);p=r(['git','push','origin','HEAD:main']);out['commit_rc']=c.returncode;out['push_rc']=p.returncode
print(json.dumps(out,indent=2))