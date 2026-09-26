"""Installeer uitsluitend eigen begrensde user-units; bestaande afwijkende units weigeren."""
import hashlib,json,os,pathlib,subprocess,tempfile,datetime
P=pathlib.Path;ROOT=P(__file__).resolve().parents[2];HERE=P(__file__).resolve().parent

def main():
    runtime=ROOT/'knowledge/codex_runtime';config=json.loads((runtime/'CONFIG.json').read_text())
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    if sha(HERE/'supervisor.py')!=config['supervisor_sha256']:raise RuntimeError('UNQUALIFIED_SUPERVISOR_SOURCE')
    dest=P.home()/'.config/systemd/user';dest.mkdir(parents=True,exist_ok=True)
    names=['prediction-codex-supervisor.service','prediction-codex-supervisor.timer']
    for name in names:
        if (dest/name).exists() and (dest/name).read_bytes()!=(HERE/'systemd'/name).read_bytes():raise RuntimeError('OWNER_UNIT_CONFLICT: '+name)
    for name in names:
        if not (dest/name).exists():
            with tempfile.NamedTemporaryFile(dir=dest,delete=False) as f:f.write((HERE/'systemd'/name).read_bytes());f.flush();os.fsync(f.fileno());tmp=P(f.name)
            os.chmod(tmp,0o644);tmp.replace(dest/name)
    subprocess.run(['systemctl','--user','daemon-reload'],check=True,timeout=30)
    subprocess.run(['systemctl','--user','enable','--now','prediction-codex-supervisor.timer'],check=True,timeout=30)
    result=subprocess.run(['systemctl','--user','show',*names,'--property=Id,ActiveState,SubState,UnitFileState,NextElapseUSecRealtime','--no-pager'],check=True,text=True,capture_output=True,timeout=30)
    receipt={'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':result.stdout,'unit_hashes':{n:sha(dest/n) for n in names},'scope':'Uitsluitend nieuwe reasoning-supervisor; geen andere timers/collectoren gewijzigd'}
    (runtime/'INSTALLATION.json').write_text(json.dumps(receipt,indent=2)+'\n');print(result.stdout)
if __name__=='__main__':main()
