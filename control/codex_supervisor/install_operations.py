"""Installeer uitsluitend eigen additive user-drop-ins, nooit een ownerunit vervangen."""
import pathlib,json,hashlib,subprocess
from supervisor import atomic
from operations import verify,ROOT,STATE
P=pathlib.Path

def install():
    verify();dest=P.home()/'.config/systemd/user'
    expected=json.loads((STATE/'OPERATIONS_DEPLOYMENT_BASIS.json').read_text())
    for name,sha in expected.items():
        p=dest/name
        if not p.is_file() or p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=sha:raise RuntimeError('OWNER_UNIT_CHANGED: '+name)
    hourly='''[Service]
ExecStartPre=
ExecStart=
ExecStartPost=
ExecStart=/usr/bin/python3 %h/prediction_research_prod/control/codex_supervisor/operations.py collect
TimeoutStartSec=5min
KillMode=control-group
'''
    delivery='''[Service]
ExecStartPost=/usr/bin/python3 %h/prediction_research_prod/control/codex_supervisor/operations.py deliver
'''
    targets={'prediction-research-hourly-director.service.d/90-isolated-local.conf':hourly,'prediction-codex-supervisor.service.d/90-local-delivery.conf':delivery}
    for name,body in targets.items():
        p=dest/name
        if p.parent.exists() and any(x!=p for x in p.parent.iterdir()):raise RuntimeError('UNKNOWN_OWNER_DROPIN: '+name)
        if p.exists() and p.read_text()!=body:raise RuntimeError('DROPIN_CONFLICT: '+name)
    atomic(STATE/'OPERATIONS_DEPLOYMENT_INTENT.json',{'original_unit_hashes':expected,'dropins':targets,'normal_unit_files_unchanged':True})
    for name,body in targets.items():
        p=dest/name
        if not p.exists():atomic(p,body)
    subprocess.run(['systemctl','--user','daemon-reload'],check=True,timeout=30)
    # Bestaande timer blijft gehandhaafd; geen push-capabele oude service starten.
    atomic(STATE/'OPERATIONS_DEPLOYED.json',{'dropins':targets,'status':'INSTALLED_NOT_YET_RUNTIME_QUALIFIED'})
    print('Drop-ins geïnstalleerd; runtime-canary blijft vereist.')
if __name__=='__main__':install()
