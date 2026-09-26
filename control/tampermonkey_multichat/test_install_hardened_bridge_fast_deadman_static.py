"""Ownerbeleid: 600s inactivity; behoud retry/fresh-task guards.

De eerdere 15s literalcheck hoorde bij 41ee276. De bewaarde staged installer
herstelt expliciet het 600s-beleid. Test de gegenereerde runtime, niet literals.
"""
import ast
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import threading

HERE=Path(__file__).resolve().parent

def test_installer_keeps_intended_inactivity_and_identity_guards():
    spec=importlib.util.spec_from_file_location('audit_policy_installer',HERE/'install_hardened_bridge.py')
    installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
    source=installer.hardened_runtime_source((HERE/'bridge_server_hardened.py').read_text())
    assert installer.hardened_runtime_source(source)==source
    tree=ast.parse(source)
    functions={'_heartbeat_interval','_maybe_enqueue_heartbeat','heartbeat_message'}
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in functions or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DEFAULT_HEARTBEAT_INTERVAL' for t in n.targets)]
    clock=[1000.0];writes=[];mode={'chat_id':'chat-test','started_at':1000.0,'last_activity_at':1000.0}
    ns={'time':SimpleNamespace(time=lambda:clock[0]),'_HEARTBEAT_LOCK':threading.Lock(),'_load_mode':lambda:mode,'_latest_route_activity':lambda _:0.0,'_atomic_json':lambda p,obj:writes.append((str(p),dict(obj))),'NIGHTSHIFT_MODE_FILE':Path('/synthetic/mode'),'base':SimpleNamespace(ROUTES=Path('/synthetic/routes'),OUTBOX=Path('/synthetic/outbox')),'secrets':SimpleNamespace(token_hex=lambda _:'synthetic-nonce')}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'generated-policy-fixture','exec'),ns)
    assert ns['DEFAULT_HEARTBEAT_INTERVAL']==installer.HEARTBEAT_IDLE_SECONDS==600.0
    clock[0]=1599.0;assert ns['_maybe_enqueue_heartbeat']('chat-test') is False
    assert writes==[]
    clock[0]=1600.0;assert ns['_maybe_enqueue_heartbeat']('chat-test') is True
    event=next(obj for path,obj in writes if '/outbox/' in path)
    assert 'synthetic-nonce' in event['message'] and 'NIEUWE' in event['message']
    clock[0]=2199.0;assert ns['_maybe_enqueue_heartbeat']('chat-test') is False
    # Nieuw bridge-/commandactiviteit schuift de volle inactivityperiode op.
    mode['last_activity_at']=2199.0
    clock[0]=2200.0;assert ns['_maybe_enqueue_heartbeat']('chat-test') is False
    clock[0]=2799.0;assert ns['_maybe_enqueue_heartbeat']('chat-test') is True
    assert ns['heartbeat_message']('nonce-A')!=ns['heartbeat_message']('nonce-B')
    for flag in ['heartbeat_retry_nonce','heartbeat_fresh_task_id_required','heartbeat_done_guard','heartbeat_inactivity_reset','heartbeat_resets_on_bridge_result','heartbeat_resets_on_assistant_command']:
        assert '"'+flag+'": True' in source
