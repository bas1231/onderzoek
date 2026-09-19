from pathlib import Path
from datetime import datetime
import json,subprocess
root=Path('.')
nl=chr(10)
script=Path('control/hourly/hourly_wake.py')
lines=['from pathlib import Path','from datetime import datetime','import json','import time','','def main():','    now = datetime.now().astimezone()','    stamp = now.strftime("%Y%m%dT%H00%z")','    iid = "hourly-research-" + stamp','    idir = Path.home() / ".local/state/prediction-research/incidents"','    idir.mkdir(parents=True, exist_ok=True)','    path = idir / (iid + "__HOURLY_RESEARCH_WAKE.json")','    if path.exists():','        return','    ts = time.time()','    data = {','        "incident_id": iid,','        "task_id": iid,','        "reason": "HOURLY_RESEARCH_WAKE",','        "detail": "Run the hourly autonomous prediction-market research director. Use only free/public sources. Route evidence through specialist agents, falsification, reproduction and publish the hourly report to Git. NO_PROVEN_EDGE is valid. No live trading, paid actions or wallet actions.",','        "status": "OPEN",','        "deliver_to_chat": True,','        "first_seen_at": ts,','        "last_seen_at": ts,','        "automatic_action": "RESEARCH_WAKE_ONLY",','        "running_task_killed": False,','        "paid_action": False,','        "live_trading_action": False,','        "wallet_action": False','    }','    path.write_text(json.dumps(data, indent=2, sort_keys=True) + chr(10))','','if __name__ == "__main__":','    main()']
script.parent.mkdir(parents=True,exist_ok=True);script.write_text(nl.join(lines)+nl)
unitdir=Path.home()/'.config/systemd/user';unitdir.mkdir(parents=True,exist_ok=True)
service='[Unit]'+nl+'Description=Prediction Research hourly director wake'+nl+nl+'[Service]'+nl+'Type=oneshot'+nl+'WorkingDirectory='+str(Path.cwd())+nl+'ExecStart='+str(Path.cwd()/'.venv/bin/python')+' '+str(Path.cwd()/script)+nl
timer='[Unit]'+nl+'Description=Prediction Research hourly director timer'+nl+nl+'[Timer]'+nl+'OnCalendar=*-*-* *:00:00'+nl+'Persistent=true'+nl+'AccuracySec=30s'+nl+'RandomizedDelaySec=0'+nl+'Unit=prediction-research-hourly-director.service'+nl+nl+'[Install]'+nl+'WantedBy=timers.target'+nl
(repo_units:=Path('control/hourly/systemd')).mkdir(parents=True,exist_ok=True)
(repo_units/'prediction-research-hourly-director.service').write_text(service)
(repo_units/'prediction-research-hourly-director.timer').write_text(timer)
(unitdir/'prediction-research-hourly-director.service').write_text(service)
(unitdir/'prediction-research-hourly-director.timer').write_text(timer)
r=lambda a:subprocess.run(a,capture_output=True,text=True,check=False)
compile_ok=r(['python3','-m','py_compile',str(script)]).returncode==0
diff_ok=r(['git','diff','--check']).returncode==0
out={'compile':compile_ok,'diff':diff_ok}
if compile_ok and diff_ok:
 r(['git','add','control/hourly']);c=r(['git','commit','-m','build(hourly): install autonomous director timer']);p=r(['git','push','origin','HEAD:main']);r(['systemctl','--user','daemon-reload']);en=r(['systemctl','--user','enable','--now','prediction-research-hourly-director.timer']);active=r(['systemctl','--user','is-active','prediction-research-hourly-director.timer']);timers=r(['systemctl','--user','list-timers','prediction-research-hourly-director.timer','--no-pager']);out.update({'commit_rc':c.returncode,'push_rc':p.returncode,'enable_rc':en.returncode,'active':active.stdout.strip(),'timer':timers.stdout.strip(),'head':r(['git','log','-1','--oneline']).stdout.strip()})
print(json.dumps(out,indent=2))