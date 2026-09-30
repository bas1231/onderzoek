from __future__ import annotations
import hashlib,importlib.util,json,re,subprocess,sys
from pathlib import Path

ROOT=Path.cwd()
BASE=ROOT/'control/dev_checks/autobuild_build_e028_runner.py'
CONFIG=ROOT/'knowledge/codex_runtime/CONFIG.json'
CONTROL=ROOT/'control/codex_supervisor'
CORE_TESTS={'tests/control/test_build_planner_nonbuildable_components.py','tests/control/test_build_planner_retry.py'}

def load_base():
    spec=importlib.util.spec_from_file_location('e028',BASE)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def sync_pins():
    raw=CONFIG.read_text(encoding='utf-8');obj=json.loads(raw);pinned=set()
    def walk(v):
        nonlocal raw
        if isinstance(v,dict):
            for k,x in v.items():
                ks=str(k)
                if isinstance(x,str) and re.fullmatch(r'[0-9a-fA-F]{64}',x) and ks.endswith('_sha256'):
                    name=ks[:-7];src=CONTROL/name
                    if src.is_file():
                        new=sha(src);pinned.add('control/codex_supervisor/'+name)
                        if x!=new:
                            pat=r'("'+re.escape(ks)+r'"\s*:\s*")'+re.escape(x)+r'(")'
                            raw,n=re.subn(pat,lambda m:m.group(1)+new+m.group(2),raw,count=1)
                            if n!=1:raise AssertionError('PIN_REWRITE_FAILED:'+ks)
                if isinstance(x,(dict,list)):walk(x)
        elif isinstance(v,list):
            for x in v:walk(x)
    walk(obj)
    if not pinned:raise AssertionError('NO_CONTROL_PLANE_PINS_FOUND')
    CONFIG.write_text(raw,encoding='utf-8')
    return pinned

def git(*args):
    cp=subprocess.run(['git',*args],cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if cp.returncode:raise SystemExit('GIT_FAIL='+' '.join(args)+':'+(cp.stdout or '')[-1200:])
    return cp.stdout or ''

def changed(paths):
    out=git('diff','--name-only','--',*sorted(paths))
    out+=git('ls-files','--others','--exclude-standard','--',*sorted(paths))
    return {x.strip() for x in out.splitlines() if x.strip()}

def main():
    base=load_base();base.prepare();pinned=sync_pins()
    summaries=[]
    summaries.append('TARGETED '+base.run_pytest('TARGETED',sorted(CORE_TESTS)))
    summaries.append('WIRING '+base.run_pytest('WIRING',['tests/codex_supervisor/test_autobuild_runtime_wiring_e004i.py']))
    summaries.append('FULL '+base.run_pytest('FULL',['tests']))
    allowed=pinned|CORE_TESTS|{'knowledge/codex_runtime/CONFIG.json'}
    stage=changed(allowed)
    required=CORE_TESTS|{'control/codex_supervisor/build_planner.py','control/codex_supervisor/candidate_dispatch.py','knowledge/codex_runtime/CONFIG.json'}
    if not required<=stage:raise SystemExit('STAGE_REQUIRED_MISSING='+repr(sorted(required-stage)))
    git('diff','--check','--',*sorted(stage));git('add','--',*sorted(stage))
    got={x.strip() for x in git('diff','--cached','--name-only').splitlines() if x.strip()}
    if got!=stage:raise SystemExit('STAGED_SET_MISMATCH='+repr(sorted(got))+' expected='+repr(sorted(stage)))
    print('AUTOBUILD_TESTS_PASS staged='+str(len(stage))+' '+' || '.join(summaries))

if __name__=='__main__':main()
