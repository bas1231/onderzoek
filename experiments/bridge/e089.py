from pathlib import Path
import json,subprocess
roles=['scout','weather_twc','microstructure','behavioral','informed_flow','algebra','settlement','prebuild_killer','chief_falsifier','independent_reproducer','research_director']
manifest={'version':1,'cadence':'hourly','status':'ACTIVE','source_policy':'free_public_only','default_candidate_status':'UNPROVEN','valid_null_result':'NO_PROVEN_EDGE','live_trading':False,'paid_actions':False,'wallet_actions':False,'pipeline':roles,'report_sections':['run_metadata','source_coverage','new_evidence','candidate_hypotheses','negative_evidence','falsification','reproduction','coverage_gaps','incidents','decision','next_hour']}
p=Path('control/hourly/director_manifest.json');p.write_text(json.dumps(manifest,indent=2,sort_keys=True)+chr(10))
q=Path('hourly-reports/README.md');q.parent.mkdir(parents=True,exist_ok=True);q.write_text('# Hourly Research Reports'+chr(10)+chr(10)+'Each run records evidence, falsification, reproduction, negative evidence, gaps and a final research status. NO_PROVEN_EDGE is valid.'+chr(10))
r=lambda a:subprocess.run(a,capture_output=True,text=True,check=False)
d=r(['git','diff','--check']);ok=d.returncode==0
out={'ok':ok,'roles':len(roles),'sections':len(manifest['report_sections'])}
if ok:
 r(['git','add',str(p),str(q)]);c=r(['git','commit','-m','build(hourly): add director routing and report schema']);z=r(['git','push','origin','HEAD:main']);out['commit_rc']=c.returncode;out['push_rc']=z.returncode;out['head']=r(['git','log','-1','--oneline']).stdout.strip()
print(json.dumps(out))