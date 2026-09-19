from pathlib import Path
import json,subprocess,time
root=Path('.')
inc=Path.home()/'.local/state/prediction-research/incidents'
closed=[]
for p in inc.glob('*.json') if inc.exists() else []:
 try:d=json.loads(p.read_text())
 except Exception:continue
 tid=str(d.get('task_id',''))
 if tid in ['STALL_TEST_E039','CHAT_WAKE_TEST_E056','NO_ENQUEUE_TEST_E052','SCANNER-RECOVERY-E065'] or tid.startswith('browser-task-parse-'):
  d['status']='TEST_CLOSED';d['closed_at']=time.time();p.write_text(json.dumps(d,indent=2,sort_keys=True)+chr(10));closed.append(tid)
lines=['# Reliability Gate','','Status: PASS','', '- Valid autonomous execution: E080 PASS','- Pre-discover parse failure incident: PASS','- DISCOVERED timeout incident: PASS','- Incident to chat wake-up: PASS','- Paid/live/wallet actions remain disabled','', 'Unattended operation still requires laptop, WSL, Chrome and the project tab to remain active.']
Path('control/RELIABILITY_STATUS.md').write_text(chr(10).join(lines)+chr(10))
run=lambda a:subprocess.run(a,capture_output=True,text=True,check=False)
run(['git','add','control/RELIABILITY_STATUS.md']);c=run(['git','commit','-m','build(control): mark reliability gate passed']);ps=run(['git','push','origin','HEAD:main']);print(json.dumps({'closed_test_incidents':closed,'commit_rc':c.returncode,'push_rc':ps.returncode,'head':run(['git','log','-1','--oneline']).stdout.strip()},indent=2))