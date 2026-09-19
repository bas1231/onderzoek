from pathlib import Path
import json,subprocess
roles=[
{'id':'scout','purpose':'Broad discovery of new public evidence, venues, papers, code and anomalies','authority':'DISCOVERY_ONLY'},
{'id':'weather_twc','purpose':'Hourly weather, TWC settlement and nowcasting research','authority':'RESEARCH_ONLY'},
{'id':'microstructure','purpose':'Orderbook, maker-taker, spread, depth and execution research','authority':'RESEARCH_ONLY'},
{'id':'behavioral','purpose':'Human bias, crowd behaviour and favorite-longshot research','authority':'RESEARCH_ONLY'},
{'id':'informed_flow','purpose':'Research informed trading and information-flow signatures','authority':'RESEARCH_ONLY'},
{'id':'algebra','purpose':'Payout identities, portfolio equivalence and formal market algebra','authority':'RESEARCH_ONLY'},
{'id':'settlement','purpose':'Rules, finality, oracle, settlement and revision research','authority':'RESEARCH_ONLY'},
{'id':'prebuild_killer','purpose':'Attempt to kill ideas before implementation','authority':'VETO_RECOMMENDATION'},
{'id':'chief_falsifier','purpose':'Adversarially falsify hypotheses and detect leakage','authority':'VETO_RECOMMENDATION'},
{'id':'independent_reproducer','purpose':'Reproduce evidence independently before promotion','authority':'VALIDATION_ONLY'},
{'id':'research_director','purpose':'Route evidence, enforce gates and publish hourly status','authority':'RESEARCH_COORDINATION'}]
policy={'version':1,'default_status':'UNPROVEN','valid_null_result':'NO_PROVEN_EDGE','live_trading':False,'paid_actions':False,'wallet_actions':False,'roles':roles}
p=Path('agents/registry.json');p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(policy,indent=2,sort_keys=True)+chr(10))
q=Path('agents/README.md');q.write_text('# Research Agents'+chr(10)+chr(10)+'Agents collect, challenge and reproduce evidence. They do not authorize spend or live trading.'+chr(10))
r=lambda a:subprocess.run(a,capture_output=True,text=True,check=False)
d=r(['git','diff','--check']);ok=d.returncode==0
out={'ok':ok,'roles':len(roles)}
if ok:
 r(['git','add','agents']);c=r(['git','commit','-m','build(agents): register research roles']);z=r(['git','push','origin','HEAD:main']);out['commit_rc']=c.returncode;out['push_rc']=z.returncode;out['head']=r(['git','log','-1','--oneline']).stdout.strip()
print(json.dumps(out))