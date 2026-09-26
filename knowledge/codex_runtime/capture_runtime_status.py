"""Uitsluitend lezen: finale service- en herstel-evidence bewaren."""
import datetime,json,pathlib,subprocess
root=pathlib.Path(__file__).resolve().parents[2]
units=['prediction-chat-command.service','prediction-chat-router.service','prediction-chat-wake.service','prediction-research-executor.service','prediction-research-lifecycle-supervisor.service','prediction-research-hourly-director.service','prediction-research-hourly-director.timer','prediction-codex-supervisor.service','prediction-codex-supervisor.timer','prediction-research-kalshi-weather-index-recorder.service','prediction-research-kalshi-weather-index-recorder.timer','prediction-research-twc-recorder.service','prediction-research-twc-recorder.timer','prediction-hourly-wiring-canary-20260926.timer','prediction-hourly-wiring-canary-20260926.service']
commands=[['systemctl','--user','show',*units,'--property=Id,LoadState,ActiveState,SubState,Result,ExecMainStatus,UnitFileState,LastTriggerUSec,NextElapseUSecRealtime','--no-pager'],['loginctl','show-user','leonh','-p','Linger'],['python3',str(root/'knowledge/codex_audit/runtime_reconcile/local_hourly/probe_bridge.py')]]
result={'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':[]}
for cmd in commands:
 p=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
 result['checks'].append({'command':cmd,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
out=root/'knowledge/codex_runtime'/('runtime_status_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.json')
out.write_text(json.dumps(result,indent=2)+'\n');print(out)
