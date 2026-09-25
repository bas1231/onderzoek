from pathlib import Path
import json,hashlib,datetime,subprocess,sys
r=Path.cwd();a=r/'knowledge/codex_audit';d=a/'canonical';m=json.loads((a/'remediation/proposal_manifest.json').read_text())
h=lambda b:hashlib.sha256(b).hexdigest()
if sys.argv[1]=='preflight':
 rows=[]
 for row in m['paths']:
  p=r/row['path'];data=p.read_bytes() if p.exists() else b''
  assert p.exists()==row['base_exists'] and h(data)==row['base_sha256'], 'DIVERGENCE '+row['path']
  proposed=(a/'remediation/proposed'/row['path']).read_bytes();assert h(proposed)==row['proposed_sha256']
  if p.exists():
   b=d/'before'/row['path'];b.parent.mkdir(parents=True,exist_ok=True);b.write_bytes(data)
  rows.append({**row,'current_matches_basis':True})
 tracked={p:h((r/p).read_bytes()) for p in subprocess.check_output(['git','ls-files','-z']).decode().split('\0') if p and (r/p).is_file()}
 (d/'preflight.json').write_text(json.dumps({'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'head':subprocess.check_output(['git','rev-parse','HEAD']).decode().strip(),'status':subprocess.check_output(['git','status','--short']).decode(),'index_diff_sha256':h(subprocess.check_output(['git','diff','--cached','--binary'])),'tracked_hashes':tracked,'paths':rows},indent=2)+'\n')
 charter={'build_id':'AUD-CANONICAL-db6c0f3','protocol_version':1,'objective':'Integreer bevestigde auditreparaties in canonical bron en kwalificeer werkelijk gedrag zonder userwerkverlies.','source_commit':subprocess.check_output(['git','rev-parse','HEAD']).decode().strip(),'allowed_capabilities':['read_repository','local_tests','repair_source','write_audit_evidence','local_git_commit'],'allowed_paths':[str(r)],'planned_paths':[x['path'] for x in rows]+['tests/audit','control/tampermonkey_multichat/test_userscript_v046_guard_static.py','knowledge/codex_audit'],'acceptance_criteria':['64 bestaande auditchecks slagen tegen canonical bron','Alle resterende failures afzonderlijk onderzocht, geen safetyassertions versoepeld','Geen userwerkverlies','Geen runtime/edge-PASS zonder bewijs'],'non_goals':['trade','push','paid services','strategy tuning','holdout mutation','service activation'],'independent_verification':'Nieuwe adversariële gedragstests na integratie; geen afzonderlijke reviewer beschikbaar.','rollback_plan':'Gerichte reverse diff alleen voor eigen reparatie na hashcontrole; voorafgaande userinhoud behouden.','cleanup_plan':'Alleen eigen tijdelijke pytest-artifacts; logs blijven.','max_attempts':5,'governance_change':False,'safety':{'live_trading':False,'paid_actions':False,'wallet_actions':False},'coordination_exception':'Gebruiker autoriseert expliciet canonical repair ondanks read-only .git; geen grensuitbreiding. Per-bestand hashcompare beschermt userwerk. Lease/worktree geblokkeerd en niet nagebootst.'}
 (d/'CHARTER.json').write_text(json.dumps(charter,indent=2)+'\n');print('All 17 source bases match; index recorded')
else:
 groups={'tests':[x['path'] for x in m['paths'] if x['path'].startswith(('tests/','knowledge/')) or '/test_' in x['path']], 'weather':['control/weather/kalshi_weather_index_recorder.py','control/weather/twc_hourly_recorder.py','control/weather/market_reaction.py','control/jobs/evaluate_kwi_full_station_checkpoint_e369.py'],'proof':['control/hourly/agent_orchestrator.py'],'bridge':['control/tampermonkey_multichat/command_router.py','control/tampermonkey_multichat/prediction-chat-wake.user.js'],'executor':['control/executor.py','control/policy_check.py','control/policy.json']}
 for name in groups[sys.argv[1]]:
  row=next(x for x in m['paths'] if x['path']==name);p=r/name;data=p.read_bytes() if p.exists() else b''
  assert h(data)==row['base_sha256'] and p.exists()==row['base_exists'],name
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((a/'remediation/proposed'/name).read_bytes())
 with (d/'integration.jsonl').open('a') as f:f.write(json.dumps({'group':sys.argv[1],'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'paths':groups[sys.argv[1]]})+'\n')
 print('Integrated',sys.argv[1])
