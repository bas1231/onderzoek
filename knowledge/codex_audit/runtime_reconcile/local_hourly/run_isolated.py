#!/usr/bin/env python3
"""Werkelijke hourly-entrypoints in een eigen Linux root/net/pid namespace."""
import concurrent.futures,time,signal
from public_broker import respond
import ctypes,datetime,hashlib,json,os,pathlib,shutil,subprocess,sys,uuid
P=pathlib.Path
ROOT=P(__file__).resolve().parents[4]
HERE=P(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(args,**kw):return subprocess.run(args,check=True,timeout=60,**kw)
def mount(*args):run(['/usr/bin/mount',*map(str,args)],stdout=subprocess.DEVNULL)

def inner(run_dir, response=False):
    out=P(run_dir);jail=out/'jail';jail.mkdir(exist_ok=True)
    mount('--make-rprivate','/')
    mount('-t','tmpfs','tmpfs',jail)
    for name in ['usr','dev','proc','etc','repo','home/research','tmp','public_io']:(jail/name).mkdir(parents=True,exist_ok=True)
    mount('--rbind','/usr',jail/'usr');mount('-o','remount,bind,ro',jail/'usr')
    for name in ['bin','sbin','lib','lib64']:
        src=P('/')/name
        if src.is_symlink():(jail/name).symlink_to(os.readlink(src))
        elif src.exists():
            (jail/name).mkdir();mount('--bind',src,jail/name);mount('-o','remount,bind,ro',jail/name)
    for name in ['null','urandom','random']:
        (jail/'dev'/name).touch();mount('--bind',P('/dev')/name,jail/'dev'/name)
    mount('-t','proc','proc',jail/'proc')
    mount('--bind',out/'broker',jail/'public_io');mount('--bind',out/'repo',jail/'repo');mount('--bind',out/'home',jail/'home/research')
    mount('-t','tmpfs','tmpfs',jail/'tmp')
    marker=json.loads((out/'source_manifest.json').read_text());marker.update(mode='qualification_local',network_namespace=os.readlink('/proc/self/ns/net'))
    (jail/'qualification.json').write_text(json.dumps(marker))
    if response:(jail/'phase_entry.py').write_bytes((HERE/'qualification_response.py').read_bytes())
    (jail/'etc/passwd').write_text('research:x:0:0:research:/home/research:/bin/sh\n')
    mount('-o','remount,bind,ro',jail)
    os.chroot(jail);os.chdir('/repo')
    # Geen mount/chroot escape: alle capabilities laten vallen vóór productiecode.
    libc=ctypes.CDLL(None,use_errno=True)
    class Header(ctypes.Structure):_fields_=[('version',ctypes.c_uint32),('pid',ctypes.c_int)]
    class Data(ctypes.Structure):_fields_=[('effective',ctypes.c_uint32),('permitted',ctypes.c_uint32),('inheritable',ctypes.c_uint32)]
    if libc.prctl(38,1,0,0,0)!=0:raise OSError('NO_NEW_PRIVS_FAILED')
    for cap in range(41):libc.prctl(24,cap,0,0,0)
    if libc.capset(ctypes.byref(Header(0x20080522,0)),(Data*2)())!=0:raise OSError('DROP_CAPS_FAILED')
    env={'HOME':'/home/research','PATH':'/usr/bin:/bin','PYTHONPATH':'/repo','PYTHONDONTWRITEBYTECODE':'1','PREDICTION_EXECUTION_MODE':'qualification_local','GIT_ALLOW_PROTOCOL':'','GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null','KALSHI_MARKET_SCAN_MAX_PAGES':'1','TZ':'UTC'}
    os.execve('/usr/bin/python3',['python3','/phase_entry.py' if response else '/repo/qualification_entry.py'],env)

def main():
    expected=json.loads((HERE/"tested_provenance.json").read_text())
    for name,digest in expected.items():
        if sha(ROOT/name)!=digest:raise RuntimeError("UNTESTED_SOURCE_CHANGE: "+name)
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    out=HERE/'runs'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]);out.mkdir(parents=True)
    repo=out/'repo';repo.mkdir();(out/'home').mkdir();(out/'broker').mkdir()
    paths=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT,text=True).split('\0')
    paths += ['control/hourly/local_runtime.py','control/hourly/local_ai_exchange.py','control/hourly/qualification_http.py']
    excluded=('knowledge/codex_audit/','knowledge/runs/','hourly-reports/','knowledge/ai_exchange/')
    copied={}
    for name in sorted(set(paths)):
        if not name or name.startswith(excluded):continue
        src=ROOT/name
        if not src.is_file() or src.is_symlink():continue
        dst=repo/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(src.read_bytes());copied[name]=sha(dst)
    data_inputs={}
    sources=[(P.home()/'prediction_research/knowledge/raw/market_data/polymarket_shadow_baselines',repo/'knowledge/raw/market_data/polymarket_shadow_baselines'),(P.home()/'.local/state/prediction-research/kalshi_weather_index_manifests',out/'home/.local/state/prediction-research/kalshi_weather_index_manifests')]
    for source,destination in sources:
        if not source.is_dir():raise RuntimeError('REQUIRED_REAL_INPUT_MISSING: '+str(source))
        destination.mkdir(parents=True,exist_ok=True)
        for item in source.glob('*.json'):
            if item.is_symlink():raise RuntimeError('INPUT_SYMLINK_FORBIDDEN')
            body=item.read_bytes();target=destination/item.name;target.write_bytes(body)
            data_inputs[str(item)]={'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'copy':str(target.relative_to(out))}
    (out/'real_input_manifest.json').write_text(json.dumps(data_inputs,indent=2)+'\n')
    (repo/'hourly-reports').mkdir(exist_ok=True);(repo/'knowledge/runs').mkdir(parents=True,exist_ok=True)
    (repo/'.venv/bin').mkdir(parents=True);(repo/'.venv/bin/python').symlink_to('/usr/bin/python3')
    shutil.copy2(HERE/'qualification_entry.py',repo/'qualification_entry.py')
    env={'PATH':'/usr/bin:/bin','HOME':str(out/'home'),'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null','GIT_ALLOW_PROTOCOL':''}
    for cmd in [['init','-b','main'],['config','user.name','Local qualification'],['config','user.email','qualification@localhost'],['add','--all'],['-c','core.hooksPath=/dev/null','-c','commit.gpgsign=false','commit','-qm','qualification: exact source snapshot']]:
        run(['/usr/bin/git',*cmd],cwd=repo,env=env,stdout=subprocess.DEVNULL)
    source={'source_hashes':{**{k:v for k,v in copied.items() if k.startswith('control/')}, 'qualification_entry.py':sha(repo/'qualification_entry.py')},'input_hashes':copied,'started_at':started}
    (out/'source_manifest.json').write_text(json.dumps(source,indent=2)+'\n')
    index=sha(ROOT/'.git/index');preserve=json.loads((HERE.parent/'preservation_manifest.json').read_text());owner={k:sha(ROOT/k) for k in preserve['owner_work']}
    command=['/usr/bin/unshare','--user','--map-root-user','--mount','--net','--pid','--fork','--kill-child','/usr/bin/python3',str(P(__file__).resolve()),'--inner',str(out)]
    with (out/'execution.log').open('w') as log, concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        proc=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        deadline=time.monotonic()+180;seen=set();pending=[]
        try:
            while proc.poll() is None:
                for request in (out/'broker').glob('*.request.json'):
                    if request.name not in seen:
                        if len(seen)>=64:raise RuntimeError('PUBLIC_REQUEST_BUDGET_EXCEEDED')
                        seen.add(request.name);pending.append(pool.submit(respond,request))
                if time.monotonic()>deadline:raise TimeoutError('HOURLY_DEADLINE')
                time.sleep(.05)
            rc=proc.returncode
        except (TimeoutError,RuntimeError):
            os.killpg(proc.pid,signal.SIGTERM);proc.wait(timeout=15);rc=124
        (out/'public_requests.json').write_text(json.dumps([p.result() for p in pending],indent=2)+'\n')
    result={'started_at':started,'exit_code':rc,'owner_preserved':index==sha(ROOT/'.git/index') and all(sha(ROOT/k)==v for k,v in owner.items()),'command':command,'qualification':'AUDIT_INCOMPLETE','scientific_status':'NO_PROVEN_EDGE','evidence_scope':'Echte lokale pipeline in kernelisolatie; geen automatische globale E2E-PASS'}
    receipt=out/'home/qualification_result.json'
    if receipt.exists():result['chain']=json.loads(receipt.read_text())
    (out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(out);print(json.dumps(result))
    return rc
if __name__=='__main__':raise SystemExit(inner(sys.argv[2],sys.argv[1]=='--inner-response') if len(sys.argv)>1 and sys.argv[1] in ('--inner','--inner-response') else main())
