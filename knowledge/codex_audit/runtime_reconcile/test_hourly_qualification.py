import importlib.util
from pathlib import Path
import subprocess
import pytest
import finalize_hourly_e2e_wsl as q

@pytest.mark.parametrize('args',[('push','origin','main'),('fetch','origin','main'),('reset','--hard'),('stash',),('clean','-fd'),('config','remote.origin.url','x'),('trade',),('wallet',),('order',),('branch','--show-current',';curl')])
def test_disallowed_operation_never_spawns(args,monkeypatch):
    monkeypatch.setattr(q.subprocess,'run',lambda *a,**k:pytest.fail('process must not launch'))
    with pytest.raises(RuntimeError,match='FORBIDS'):q.readonly_git(*args)

def test_changed_provenance_refused(tmp_path):
    p=tmp_path/'source.py';p.write_text('before');manifest={'source.py':q.sha(p)};p.write_text('after')
    with pytest.raises(RuntimeError,match='PROVENANCE'):q.verify(tmp_path,manifest)
    assert p.read_text()=='after'

def test_original_guard_blocks_and_never_runs_downstream(monkeypatch):
    path=q.ROOT/'control/hourly/runtime_sync.py';spec=importlib.util.spec_from_file_location('test_original_sync',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    calls=[]
    def read(*args):
        calls.append(args)
        if args==('branch','--show-current'):return subprocess.CompletedProcess(args,0,'main\n','')
        if args==('diff','--cached','--name-only','--'):return subprocess.CompletedProcess(args,0,'owner.py\n','')
        pytest.fail('No operation after owner-index refusal')
    monkeypatch.setattr(q,'readonly_git',read)
    result=q.assess(m)
    assert result['status']=='BLOCKED' and 'index is not empty: owner.py' in result['error']
    assert len(calls)==2

def test_readonly_git_does_not_enable_hooks_or_network(monkeypatch):
    def run(cmd,**kw):
        assert cmd==['/usr/bin/git','-c','core.fsmonitor=false','-c','core.hooksPath=/dev/null','branch','--show-current']
        assert kw['env']['GIT_OPTIONAL_LOCKS']=='0' and kw['env']['GIT_ALLOW_PROTOCOL']==''
        return subprocess.CompletedProcess(cmd,0,'main\n','')
    monkeypatch.setattr(q.subprocess,'run',run)
    assert q.readonly_git('branch','--show-current').returncode==0
