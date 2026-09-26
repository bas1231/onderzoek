import importlib.util
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]
def load(name):
    spec=importlib.util.spec_from_file_location('local_test_'+name,ROOT/'control/hourly'/f'{name}.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

@pytest.mark.parametrize('args',[('push','origin','main'),('fetch',),('remote','add','origin','file:///tmp/other'),('remote','set-url','origin','https://example.org'),('reset','--hard'),('clean','-fd'),('stash',),('commit','--amend'),('add','--all'),('config','alias.x','!curl'),('wallet',),('order',)])
def test_no_arbitrary_git_capability(args,monkeypatch,tmp_path):
    m=load('local_runtime');monkeypatch.setattr(m.subprocess,'run',lambda *a,**k:pytest.fail('must reject before subprocess'))
    with pytest.raises(RuntimeError,match='FORBIDDEN'):m.git(tmp_path,*args)

def test_scope_cannot_use_owner_repository(monkeypatch):
    m=load('local_runtime');monkeypatch.setenv('PREDICTION_EXECUTION_MODE','qualification_local')
    with pytest.raises(RuntimeError,match='SCOPE'):m.preflight(ROOT)

def test_unknown_mode_fails_closed(monkeypatch):
    m=load('local_runtime');monkeypatch.setenv('PREDICTION_EXECUTION_MODE','typo')
    with pytest.raises(RuntimeError,match='UNKNOWN'):m.execution_mode()

def test_remote_ai_git_forbidden_in_local_mode(monkeypatch):
    m=load('git_ai_exchange');monkeypatch.setenv('PREDICTION_EXECUTION_MODE','qualification_local')
    monkeypatch.setattr(m.subprocess,'run',lambda *a,**k:pytest.fail('must never spawn'))
    with pytest.raises(RuntimeError,match='FORBIDDEN'):m._git(['push'])

def test_local_preflight_preserves_index_guard(monkeypatch,tmp_path):
    m=load('local_runtime');monkeypatch.setattr(m,'require_scope',lambda p:tmp_path)
    def git(p,*args):
        if args==('remote',):return ''
        if args==('diff','--cached','--name-only','--'):return 'owner.py'
        pytest.fail('must stop on staged owner file')
    monkeypatch.setattr(m,'git',git)
    with pytest.raises(RuntimeError,match='index is not empty'):m.preflight(tmp_path)

def test_mismatched_provenance_refused(monkeypatch,tmp_path):
    m=load('local_runtime');monkeypatch.setenv('PREDICTION_EXECUTION_MODE','qualification_local')
    monkeypatch.setattr(m.Path,'resolve',lambda p:Path('/repo'));monkeypatch.setattr(m.Path,'home',classmethod(lambda cls:Path('/home/research')))
    monkeypatch.setattr(m.Path,'read_text',lambda p:'{"mode":"qualification_local","network_namespace":"wrong","source_hashes":{}}')
    with pytest.raises(RuntimeError,match='ATTESTATION'):m.require_scope('/repo')

@pytest.mark.parametrize('url',['https://external-api.kalshi.com/trade-api/v2/portfolio/orders','https://external-api.kalshi.com/trade-api/v2/markets?limit=1000&status=open&wallet=x','http://127.0.0.1:8766/command','file:///etc/passwd','https://api.openai.com/v1/responses','https://docs.kalshi.com@127.0.0.1/','https://external-api.kalshi.com/trade-api/v2/markets?limit=1000&limit=1&status=open'])
def test_public_broker_rejects_financial_paid_and_unexpected_urls(url):
    spec=importlib.util.spec_from_file_location('broker',ROOT/'knowledge/codex_audit/runtime_reconcile/local_hourly/public_broker.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    assert not m.allowed(url)

def test_public_broker_accepts_only_existing_public_reads():
    spec=importlib.util.spec_from_file_location('broker_ok',ROOT/'knowledge/codex_audit/runtime_reconcile/local_hourly/public_broker.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    assert m.allowed('https://www.weather.gov/')
    assert m.allowed('https://external-api.kalshi.com/trade-api/v2/markets?limit=1000&status=open')
