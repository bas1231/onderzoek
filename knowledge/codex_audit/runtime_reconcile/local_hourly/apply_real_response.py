"""Enkel aantoonbaar echte supervisorcompletion naar de bijbehorende isolatierun."""
import fcntl,hashlib,json,pathlib,subprocess,sys
P=pathlib.Path;HERE=P(__file__).resolve().parent;ROOT=HERE.parents[3]
def main():
 run=(ROOT/sys.argv[1]).resolve();completion=(ROOT/sys.argv[2]).resolve()
 if not run.is_relative_to(HERE/'runs') or not completion.is_relative_to(ROOT/'knowledge/codex_runtime/runs'):raise RuntimeError('PATH_SCOPE')
 with (run/'response.lock').open('a+') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  c=json.loads(completion.read_text());task=json.loads((completion.parent/'TASK.json').read_text())
  if c['input_sha256']!=hashlib.sha256(task['prompt'].encode()).hexdigest():raise RuntimeError('MODEL_INPUT_CHANGED')
  response=json.loads(c['final']);req=json.loads((run/'repo/knowledge/ai_exchange/requests'/f"{response['run_id']}.json").read_text())
  if response['response_token']!=req['response_token']:raise RuntimeError('MODEL_RESPONSE_TOKEN_MISMATCH')
  out=run/'repo/knowledge/ai_exchange/responses'/f"{response['run_id']}.json";out.parent.mkdir(parents=True,exist_ok=True)
  envelope={'schema':'PVA_AI_EXCHANGE_RESPONSE_V1','run_id':response['run_id'],'request_sha256':req['request_sha256'],'response':response}
  if out.exists() and json.loads(out.read_text())!=envelope:raise RuntimeError('CONFLICTING_EXISTING_RESPONSE')
  if not out.exists():out.write_text(json.dumps(envelope,indent=2)+'\n')
  cmd=['/usr/bin/unshare','--user','--map-root-user','--mount','--net','--pid','--fork','--kill-child','/usr/bin/python3',str(HERE/'run_isolated.py'),'--inner-response',str(run)]
  with (run/'response_execution.log').open('a') as log:proc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=90)
  record={'exit_code':proc.returncode,'completion_ref':str(completion.relative_to(ROOT)),'completion_sha256':hashlib.sha256(completion.read_bytes()).hexdigest(),'model_thread_id':c['thread_id'],'run_id':response['run_id'],'source':'REAL_CHATGPT_AUTHENTICATED_CODEX_RESPONSE'}
  (run/'RESPONSE_PROVENANCE.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record));return proc.returncode
if __name__=='__main__':raise SystemExit(main())
