"""Werkelijke receiver, orchestration en checkpoint voor een echte modelresponse."""
import json,sys
from pathlib import Path
sys.path.insert(0,'/repo')
from control.hourly.local_runtime import require_scope,checkpoint
from control.hourly.local_ai_exchange import ingest_local_responses
require_scope('/repo')
result=ingest_local_responses()
if not result.get('ok') or not result.get('applied'):
    Path('/home/research/response_result.json').write_text(json.dumps(result,indent=2)+'\n')
    raise SystemExit(1)
result['checkpoint']=checkpoint('/repo')
Path('/home/research/response_result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':result['status'],'response_count':len(result['applied']),'checkpoint':result['checkpoint']}))
