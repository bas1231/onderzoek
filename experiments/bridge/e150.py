from pathlib import Path
import json,subprocess
R=Path.cwd()
runp=R/'knowledge/runs/hourly-20260920T000000+0200.json'
run=json.loads(runp.read_text())
rows=[]
for sid,mref in run.get('source_manifests',{}).items():
 m=json.loads(Path(mref).read_text())
 sha=m.get('sha256')
 tp=R/'knowledge/documents/text'/sid/(str(sha)+'.json')
 chars=0
 if tp.exists():
  chars=int(json.loads(tp.read_text()).get('chars') or 0)
 status='USABLE' if chars>=500 else 'LOW_TEXT_YIELD'
 rows.append(dict(source_id=sid,status=status,chars=chars,document_sha256=sha,text_ref=str(tp.relative_to(R)) if tp.exists() else None))
out=dict(run_id=run.get('run_id'),usable_count=sum(1 for x in rows if x.get('status')=='USABLE'),low_text_yield_count=sum(1 for x in rows if x.get('status')=='LOW_TEXT_YIELD'),sources=rows,rule='LOW_TEXT_YIELD may not support a research claim')
qp=R/'knowledge/runs/hourly-20260920T000000+0200-source-quality.json'
qp.write_text(json.dumps(out,indent=2,sort_keys=True)+chr(10))
rp=R/'hourly-reports/hourly-20260920T000000+0200.md'
with rp.open('a') as f:
 f.write(chr(10)+'## Source usability'+chr(10)+chr(10))
 f.write('Usable: '+str(out.get('usable_count'))+chr(10))
 f.write('Low-text-yield: '+str(out.get('low_text_yield_count'))+chr(10))
 for x in rows:
  if x.get('status')=='LOW_TEXT_YIELD': f.write('- '+x.get('source_id')+': LOW_TEXT_YIELD ('+str(x.get('chars'))+' chars)'+chr(10))
r=lambda a:subprocess.run(a,capture_output=True,text=True,check=False)
d=r(['git','diff','--check']);assert d.returncode==0,d.stderr;r(['git','add',str(qp),str(rp)]);c=r(['git','commit','-m','run(hourly): grade midnight source usability']);p=r(['git','push','origin','HEAD:main']);print(json.dumps(dict(ok=True,usable=out.get('usable_count'),low=out.get('low_text_yield_count'),low_sources=[x.get('source_id') for x in rows if x.get('status')=='LOW_TEXT_YIELD'],commit_rc=c.returncode,push_rc=p.returncode),indent=2))