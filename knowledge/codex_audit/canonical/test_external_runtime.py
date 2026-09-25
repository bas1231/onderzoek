"""Alleen tijdelijke loopbackservers; nooit een bestaande bridge/queue wijzigen."""
import contextlib
import http.client
import importlib.util
import json
from pathlib import Path
import threading

ROOT=Path(__file__).resolve().parents[3]

@contextlib.contextmanager
def router_server(root):
    spec=importlib.util.spec_from_file_location('qualification_router',''+str(ROOT/'control/tampermonkey_multichat/command_router.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.ROUTES=root;root.mkdir(exist_ok=True)
    module.forward_command=lambda *a:(200,{'ok':True,'synthetic_upstream':True})
    module.Handler.log_message=lambda *a:None
    server=module.ThreadingHTTPServer(('127.0.0.1',0),module.Handler)
    server.bridge_token='synthetic-qualification-only';server.daemon_threads=True
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield server.server_address[1]
    finally:
        server.shutdown();server.server_close();thread.join(timeout=3)
        assert not thread.is_alive()

def post(port,payload):
    connection=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
    try:
        connection.request('POST','/command',json.dumps(payload).encode(),{'Authorization':'Bearer synthetic-qualification-only','Content-Type':'application/json'})
        response=connection.getresponse();return response.status,json.loads(response.read())
    finally:connection.close()

def test_real_router_socket_envelope_and_restart_persistence(tmp_path):
    routes=tmp_path/'routes'
    request={'task_id':'SYNTHETIC-QUALIFICATION','chat_id':'chat-test','consumer_id':'tab-test','action':'BRIDGE_PING'}
    with router_server(routes) as port:
        assert post(port,[])[0]==400
        assert list(routes.iterdir())==[]
        status,body=post(port,request)
        assert status==200 and body['ok'] and body['routed']
        original=(routes/'SYNTHETIC-QUALIFICATION.json').read_bytes()
    # Nieuw geladen module en nieuwe listener: geen production restart.
    with router_server(routes) as port:
        assert post(port,request)[0]==200
        assert (routes/'SYNTHETIC-QUALIFICATION.json').read_bytes()==original
        assert post(port,{**request,'chat_id':'chat-other'})[0]==409
        (routes/'SYNTHETIC-CORRUPT.json').write_text('{')
        assert post(port,{**request,'task_id':'SYNTHETIC-CORRUPT'})[0]==409
        assert (routes/'SYNTHETIC-CORRUPT.json').read_text()=='{'
