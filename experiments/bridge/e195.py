from pathlib import Path
import json
import subprocess
root=Path.cwd()
home=Path.home()
name='prediction-research-twc-recorder.service'
repo=root/'control/weather/systemd'/name
user=home/'.config/systemd/user'/name
text=repo.read_text(encoding='utf-8')
post='ExecStartPost=%h/prediction_research/.venv/bin/python %h/prediction_research/control/jobs/twc_revision_summary.py'
lines=text.splitlines()
lines=[x for x in lines if not x.startswith('ExecStartPost=')]
out=[]
for x in lines:
    out.append(x)
    if x.startswith('ExecStart='):
        out.append(post)
new='
'.join(out)+'
'
repo.write_text(new,encoding='utf-8')
user.write_text(new,encoding='utf-8')
def run(a):
    p=subprocess.run(a,capture_output=True,text=True,check=False)
    return {'rc':p.returncode,'stdout':p.stdout.strip(),'stderr':p.stderr.strip()}
verify=run(['systemd-analyze','--user','verify',str(user)])
reload=run(['systemctl','--user','daemon-reload'])
status=run(['systemctl','--user','cat',name])
if verify['rc']!=0 or reload['rc']!=0:
    print(json.dumps({'verify':verify,'reload':reload,'status':status},indent=2))
    raise SystemExit(1)
run(['git','add',str(repo)])
commit=run(['git','commit','-m','build(weather): summarize TWC revisions after each snapshot'])
push=run(['git','push','origin','HEAD:main'])
print(json.dumps({'verify':verify,'reload':reload,'status':status,'commit':commit,'push':push,'live_trading':False,'paid_actions':False,'wallet_actions':False},indent=2))
if push['rc']!=0:
    raise SystemExit(push['rc'])