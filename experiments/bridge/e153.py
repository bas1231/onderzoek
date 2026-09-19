from pathlib import Path
import json,subprocess
R=Path.cwd()
rp=R/'knowledge/runs/hourly-20260920T000000+0200.json'
d=json.loads(rp.read_text())
review=dict(weather_twc=dict(status='NO_EVIDENCE',reason='Meteorological source availability only; no TWC settlement mapping or market-edge evidence.'),microstructure=dict(status='NO_EVIDENCE',reason='Keyword routing produced generic regulatory and false-positive ask matches; no executable microstructure edge.'),behavioral=dict(status='NO_EVIDENCE',reason='Bias match referred to bias-corrected weather products, not behavioral prediction-market bias.'),informed_flow=dict(status='NO_EVIDENCE',reason='Flow matches referred to aviation traffic flow and software workflows, not informed trading flow.'),algebra=dict(status='NO_EVIDENCE',reason='Polymarket combo documentation shows platform capability only; no payoff identity or executable mispricing proved.'),settlement=dict(status='NO_EVIDENCE',reason='Generic final/resolution terms did not establish a settlement-specific edge.'),scout=dict(status='NO_EVIDENCE',reason='Discovery material only; no candidate survived semantic relevance review.'))
for k,v in review.items(): d.get('agents').update({k:v.get('status')})
d.get('agents').update(dict(prebuild_killer='COMPLETED',chief_falsifier='NO_EVIDENCE',independent_reproducer='NO_EVIDENCE',research_director='COMPLETED'))
d.get('gates').update(dict(signal_edge='NOT_TESTED',market_edge='NOT_TESTED',execution_reality='NOT_TESTED',falsification='NOT_TESTED',reproduction='NOT_TESTED'))
d.update(dict(status='COMPLETED',candidate_status='UNPROVEN',decision='NO_PROVEN_EDGE',semantic_review=review))
rp.write_text(json.dumps(d,indent=2,sort_keys=True)+chr(10))
report=R/'hourly-reports/hourly-20260920T000000+0200.md'
with report.open('a') as f:
 f.write(chr(10)+'## Semantic review'+chr(10)+chr(10)+'Keyword hits were manually checked for domain relevance. Current routing produced multiple false positives and no candidate survived semantic review.'+chr(10)+chr(10)+'Pre-Build Killer: PASS - no build candidate'+chr(10)+'Chief Falsifier: NOT_TESTED - no surviving claim'+chr(10)+'Independent Reproducer: NOT_TESTED - no surviving claim'+chr(10)+'Decision: NO_PROVEN_EDGE'+chr(10))
out=R/'knowledge/runs/hourly-20260920T000000+0200-semantic-review.json'
out.write_text(json.dumps(dict(run_id=d.get('run_id'),decision='NO_PROVEN_EDGE',review=review),indent=2,sort_keys=True)+chr(10))
r=lambda a:subprocess.run(a,capture_output=True,text=True,check=False)
x=r(['git','diff','--check']);assert x.returncode==0,x.stderr;r(['git','add',str(rp),str(report),str(out)]);c=r(['git','commit','-m','run(hourly): record midnight semantic falsification']);p=r(['git','push','origin','HEAD:main']);print(json.dumps(dict(ok=True,decision='NO_PROVEN_EDGE',surviving_candidates=0,commit_rc=c.returncode,push_rc=p.returncode),indent=2))