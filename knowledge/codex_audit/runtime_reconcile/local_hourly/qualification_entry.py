"""Namespace-entrypoint: echte preflight, wrapper, lokale checkpoint; geen mocks."""
import json,os,pathlib,socket,subprocess,datetime
r=pathlib.Path('/repo');result={'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'stages':[]}
def save():(pathlib.Path('/home/research')/'qualification_result.json').write_text(json.dumps(result,indent=2)+'\n')
# Eerst actieve negatieve probes; geen plaintext credentials of hostmounts aanwezig.
checks={}
checks['owner_home_absent']=not pathlib.Path('/home/leonh').exists()
try:pathlib.Path('/qualification.json').write_text('unsafe');checks['root_readonly']=False
except OSError:checks['root_readonly']=True
s=None
try:
    s=socket.socket();s.settimeout(1);s.connect(('1.1.1.1',443));checks['external_network_blocked']=False
except OSError:checks['external_network_blocked']=True
finally:
    if s is not None:s.close()
checks['no_capabilities']=all(int(line.split()[1],16)==0 for line in pathlib.Path('/proc/self/status').read_text().splitlines() if line.startswith(('CapEff:','CapPrm:')))
checks['no_remote']=subprocess.check_output(['git','remote'],text=True).strip()==''
result['isolation_checks']=checks;save()
if not all(checks.values()):raise SystemExit(90)
for name in ['runtime_sync.py','edge_hunter_cycle.py']:
    p=subprocess.run(['/usr/bin/python3',str(r/'control/hourly'/name)],cwd=r,check=False)
    result['stages'].append({'entrypoint':name,'exit_code':p.returncode});save()
    if p.returncode!=0:raise SystemExit(p.returncode)
result['wrapper_completed']=True
result['model_roundtrip']='UNPROVEN'
result['finished_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
