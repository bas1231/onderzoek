from pathlib import Path
import json,subprocess
contracts={
'scout':{'input':'source registry plus prior hour state','output':['leads','source_changes','coverage_gaps'],'gate':'discovery_only'},
'weather_twc':{'input':'weather and settlement leads','output':['signal_hypotheses','point_in_time_risks','negative_evidence'],'gate':'signal_edge_only_until_market_test'},
'microstructure':{'input':'venue and orderbook evidence','output':['execution_constraints','market_hypotheses','negative_evidence'],'gate':'executable_evidence_required'},
'behavioral':{'input':'behavioral evidence','output':['bias_hypotheses','counterevidence'],'gate':'no_unverified_generalization'},
'informed_flow':{'input':'flow evidence','output':['flow_hypotheses','confounders'],'gate':'no_insider_assumption_as_fact'},
'algebra':{'input':'contract and payout structures','output':['candidate_identities','formal_conditions'],'gate':'statewise_payout_proof_required'},
'settlement':{'input':'rules and oracle evidence','output':['settlement_constraints','finality_risks'],'gate':'primary_rules_preferred'},
'prebuild_killer':{'input':'all new candidates','output':['kill_tests','fatal_flaws'],'gate':'attempt_rejection_first'},
'chief_falsifier':{'input':'surviving candidates','output':['falsification_tests','leakage_checks'],'gate':'reject_on_unresolved_leakage'},
'independent_reproducer':{'input':'surviving evidence packages','output':['reproduction_status','discrepancies'],'gate':'independent_confirmation_required'},
'research_director':{'input':'all agent outputs','output':['hourly_report','candidate_status','next_hour_queue'],'gate':'NO_PROVEN_EDGE_is_valid'}
}
root=Path('agents/contracts');root.mkdir(parents=True,exist_ok=True)
for k,v in contracts.items():(root/(k+'.json')).write_text(json.dumps({'agent':k,**v,'live_trading':False,'paid_actions':False,'wallet_actions':False},indent=2,sort_keys=True)+chr(10))
r=lambda a:subprocess.run(a,capture_output=True,text=True,check=False)
d=r(['git','diff','--check']);out={'ok':d.returncode==0,'contracts':len(contracts)}
if out['ok']:
 r(['git','add','agents/contracts']);c=r(['git','commit','-m','build(agents): add operational research contracts']);z=r(['git','push','origin','HEAD:main']);out['commit_rc']=c.returncode;out['push_rc']=z.returncode;out['head']=r(['git','log','-1','--oneline']).stdout.strip()
print(json.dumps(out))