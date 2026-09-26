import importlib.util,json,pathlib,sys
import pytest
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'control/codex_supervisor'))
import operations as op

def fixture(tmp_path):
    p=tmp_path/'repo/knowledge/ai_exchange/requests';p.mkdir(parents=True)
    (p/'request.json').write_text(json.dumps({'run_id':'test','expected_response_schema':{},'response_token':'token'}))
    result={'exit_code':0,'owner_preserved':True,'started_at':'2026-09-26','chain':{'isolation_checks':dict.fromkeys(['owner_home_absent','root_readonly','external_network_blocked','no_capabilities','no_remote'],True)}}
    (tmp_path/'RESULT.json').write_text(json.dumps(result));return result

@pytest.mark.parametrize('field',['owner_home_absent','root_readonly','external_network_blocked','no_capabilities','no_remote'])
def test_isolation_fail_closed(tmp_path,field):
    r=fixture(tmp_path);r['chain']['isolation_checks'][field]=False
    (tmp_path/'RESULT.json').write_text(json.dumps(r))
    with pytest.raises(op.Blocked):op.task_for(tmp_path)

def test_owner_must_be_preserved(tmp_path):
    r=fixture(tmp_path);r['owner_preserved']=False;(tmp_path/'RESULT.json').write_text(json.dumps(r))
    with pytest.raises(op.Blocked):op.task_for(tmp_path)

def test_failed_wrapper_cannot_enqueue(tmp_path):
    r=fixture(tmp_path);r['exit_code']=1;(tmp_path/'RESULT.json').write_text(json.dumps(r))
    with pytest.raises(op.Blocked):op.task_for(tmp_path)

def test_unique_request_required(tmp_path):
    fixture(tmp_path);(tmp_path/'repo/knowledge/ai_exchange/requests/extra.json').write_text('{}')
    with pytest.raises(op.Blocked):op.task_for(tmp_path)

def test_task_deterministic_and_bounded(tmp_path,monkeypatch):
    fixture(tmp_path);monkeypatch.setattr(op,'ROOT',tmp_path.parent)
    a=op.task_for(tmp_path);assert a==op.task_for(tmp_path)
    assert a['input_sha256']==op.digest(a['prompt'].encode())
    assert 'local_tasks blijft leeg' in a['prompt']

def test_unknown_operation_fails_closed(monkeypatch):
    monkeypatch.setattr(op,'verify',lambda:None);monkeypatch.setattr(sys,'argv',['operations.py','push'])
    with pytest.raises(op.Blocked,match='UNEXPECTED_OPERATION'):op.main()

def test_provenance_mismatch(tmp_path,monkeypatch):
    monkeypatch.setattr(op,'verify_installation',lambda _:None);monkeypatch.setattr(op,'STATE',tmp_path);monkeypatch.setattr(op,'ROOT',tmp_path)
    (tmp_path/'source').write_text('changed');(tmp_path/'OPERATIONS_PROVENANCE.json').write_text('{"source":"wrong"}')
    with pytest.raises(op.Blocked,match='PROVENANCE'):op.verify()

def test_delivery_never_executes_model_next_action(tmp_path,monkeypatch):
    import inspect
    source=inspect.getsource(op.deliver)
    assert "response['candidate_decisions']" in source
    assert "'local_execution_authorized':False" in source
    assert 'shell=True' not in source

def test_installer_rejects_owner_unit_change(tmp_path,monkeypatch):
    import install_operations as install
    monkeypatch.setattr(install,'verify',lambda:None)
    monkeypatch.setattr(install,'STATE',tmp_path)
    monkeypatch.setattr(pathlib.Path,'home',lambda:tmp_path)
    unit=tmp_path/'.config/systemd/user/owner.service';unit.parent.mkdir(parents=True);unit.write_text('owner intent')
    (tmp_path/'OPERATIONS_DEPLOYMENT_BASIS.json').write_text('{"owner.service":"old hash"}')
    with pytest.raises(RuntimeError,match='OWNER_UNIT_CHANGED'):install.install()
    assert unit.read_text()=='owner intent'

def test_busy_worker_keeps_durable_outbox(tmp_path,monkeypatch):
    fixture(tmp_path);monkeypatch.setattr(op,'ROOT',tmp_path.parent)
    class Busy:
        def __init__(self,*args):pass
        def enqueue(self,t):raise op.Blocked('WORKER_ALREADY_RUNNING')
    monkeypatch.setattr(op,'Supervisor',Busy)
    op.enqueue_run(tmp_path)
    assert json.loads((tmp_path/'AUTO_ENQUEUE_PENDING.json').read_text())['input_sha256']==op.task_for(tmp_path)['input_sha256']
    assert not (tmp_path/'AUTO_TASK.json').exists()
