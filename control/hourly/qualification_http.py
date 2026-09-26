"""GET-only openbare brokerclient; geen socket/netwerk in researchnamespace."""
import base64,hashlib,json,os,time,uuid
from pathlib import Path

def fetch(url,timeout=20):
    if os.environ.get('PREDICTION_EXECUTION_MODE')!='qualification_local':raise RuntimeError('QUALIFICATION_ONLY')
    folder=Path('/public_io');request_id=uuid.uuid4().hex
    path=folder/(request_id+'.request.json');tmp=folder/(request_id+'.tmp')
    tmp.write_text(json.dumps({'url':url}));tmp.replace(path)
    response=folder/(request_id+'.response.json');deadline=time.monotonic()+timeout+5
    while not response.exists():
        if time.monotonic()>deadline:raise TimeoutError('PUBLIC_BROKER_TIMEOUT')
        time.sleep(.05)
    data=json.loads(response.read_text())
    if data.get('url')!=url or not data.get('ok'):raise RuntimeError('PUBLIC_BROKER_REJECTED: '+str(data.get('error_type','identity')))
    body=base64.b64decode(data['body'],validate=True)
    if hashlib.sha256(body).hexdigest()!=data['sha256']:raise RuntimeError('PUBLIC_BODY_HASH_MISMATCH')
    return body,data['headers'],data['status']
