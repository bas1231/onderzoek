from pathlib import Path
import json,subprocess
protocol={'version':1,'research_only':True,'gates':['source_provenance','point_in_time','signal_edge','market_edge','execution_reality','prebuild_killer','chief_falsifier','independent_reproducer'],'promotion_rule':'No candidate may be called proven unless every required gate passes out of sample.','null_result':'NO_PROVEN_EDGE','evidence_priority':['official_primary','academic_primary','reputable_secondary','code_repository','community_discovery'],'community_rule':'Community and video sources are discovery leads only until independently supported.','weather_rule':'Predict TWC settlement value as black box; do not equate objective weather truth with settlement.','market_rule':'A meteorological forecasting improvement without executable market mispricing is not a trading edge.','forbidden':['paid_action_without_explicit_approval','live_trading','wallet_action','post_close_information_leakage','post_hoc_profit_optimization']}
p=Path('control/hourly/research_protocol.json');p.write_text(json.dumps(protocol,indent=2,sort_keys=True)+chr(10))
r=lambda a:subprocess.run(a,capture_output=True,text=True,check=False)
d=r(['git','diff','--check']);out={'ok':d.returncode==0,'gates':len(protocol['gates'])}
if out['ok']:
 r(['git','add',str(p)]);c=r(['git','commit','-m','build(hourly): define research gate protocol']);z=r(['git','push','origin','HEAD:main']);out['commit_rc']=c.returncode;out['push_rc']=z.returncode;out['head']=r(['git','log','-1','--oneline']).stdout.strip()
print(json.dumps(out))