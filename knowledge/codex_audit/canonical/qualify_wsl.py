#!/usr/bin/env python3
"""Veilige externe WSL-kwalificatie: offline fixtures + read-only runtimebewijs.

Geen install/deploy/restart/start/stop, geen queuewijzigingen, geen /next,
geen live POST, geen Gitmutatie/push, geen externe API. Alleen eigen tijdelijke
servers gebruiken loopback; bestaande services uitsluitend GET /health.
"""
import datetime as dt
import hashlib
import http.client
import json
import os
from pathlib import Path
import subprocess
import tempfile
import uuid

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    started=dt.datetime.now(dt.timezone.utc)
    out=HERE/'external_runs'/(started.strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8])
    out.mkdir(parents=True,exist_ok=False)
    report={'started_at':started.isoformat(),'scope':'Offline canonical tests, temporary loopback, read-only deployed health/systemd/receipts','runtime_e2e':'UNPROVEN','execution_context':'LOCAL_INVOCATION_UNATTESTED','runner_sha256':sha(Path(__file__)),'scientific_status':'NO_PROVEN_EDGE','checks':[]}
    def save():
        (out/'RESULT.json').write_text(json.dumps(report,indent=2)+'\n')
    def command(label,args,env=None,log=False):
        try:
            proc=subprocess.run(args,cwd=ROOT,env=env,text=True,capture_output=True,timeout=240)
            row={'label':label,'command':args,'exit_code':proc.returncode}
            if log:
                (out/(label+'.log')).write_text(proc.stdout+proc.stderr)
                row['log']=label+'.log'
            else:
                # Alleen vaste veilige opdrachten/selecties; nooit environment/token/logdump.
                row['stdout']=proc.stdout;row['stderr']=proc.stderr
        except subprocess.TimeoutExpired:row={'label':label,'command':args,'status':'TIMEOUT_240'}
        except OSError as exc:row={'label':label,'command':args,'status':'BLOCKED','error_type':type(exc).__name__}
        report['checks'].append(row);save();return row
    save()
    command('git_head',['git','rev-parse','HEAD'])
    command('git_status',['git','status','--short'])
    manifest=json.loads((HERE/'canonical_change_manifest.json').read_text())
    report['tested_repair_hashes']=[{'path':x['path'],'matches':(ROOT/x['path']).is_file() and sha(ROOT/x['path'])==x['canonical_sha256']} for x in manifest['paths']]
    if not all(x['matches'] for x in report['tested_repair_hashes']):
        report['preflight']='SOURCE_DIVERGED';save();print('STOP: bron wijkt af; evidence:',out);return 2
    python=ROOT/'.venv/bin/python'
    # Geen dependency-installatie en geen betaalde fallback.
    if not python.is_file():
        report['preflight']='VENV_MISSING';save();print('STOP: .venv ontbreekt; evidence:',out);return 2
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(ROOT)+':'+str(ROOT/'control/weather'),PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
    scopes={
        'offline_contracts':['tests/audit','knowledge/codex_audit/evidence/test_audit_regressions.py','control/weather','tests/hourly/test_agent_orchestrator.py','control/tampermonkey_multichat/test_install_hardened_bridge_fast_deadman_static.py'],
        'real_loopback':['control/tampermonkey_multichat/test_bridge_server_sent_semantics.py','knowledge/codex_audit/canonical/test_external_runtime.py'],
    }
    with tempfile.TemporaryDirectory(prefix='codex-wsl-qualification-') as tmp:
        for label,paths in scopes.items():
            command(label,[str(python),'-m','pytest','-q',*paths,'--tb=short','-o','cache_dir='+tmp+'/cache','--basetemp='+tmp+'/'+label],env,True)
    units=['prediction-chat-wake.service','prediction-chat-router.service','prediction-research-executor.service','prediction-research-hourly-director.service','prediction-research-hourly-director.timer','prediction-runtime-sync.service','prediction-research-kalshi-weather-index-recorder.service','prediction-research-twc-recorder.service']
    command('systemd_observation',['systemctl','--user','show',*units,'--property=Id,LoadState,ActiveState,SubState,MainPID,NRestarts,ActiveEnterTimestamp,ExecMainStatus,LastTriggerUSec,NextElapseUSecRealtime','--no-pager'])
    # Alleen bekende localhost GET health; geen redirects of externe hosts.
    tokenfile=Path.home()/'.config/prediction-chat-bridge/token'
    try:token=tokenfile.read_text().strip()
    except OSError:token=''
    health=[]
    allowed={'ok','service','version','server_heartbeat','heartbeat_interval_seconds','heartbeat_done_guard','heartbeat_inactivity_reset','heartbeat_resets_on_bridge_result','heartbeat_resets_on_assistant_command','heartbeat_retry_nonce','heartbeat_fresh_task_id_required','consumer_routing','upstream_port'}
    for port in (8765,8767):
        entry={'port':port,'method':'GET','path':'/health'}
        connection=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
        try:
            connection.request('GET','/health',headers={'Authorization':'Bearer '+token} if token else {})
            response=connection.getresponse();entry['http_status']=response.status
            data=json.loads(response.read(65536))
            entry['selected_fields']={k:v for k,v in data.items() if k in allowed and (isinstance(v,(bool,int,float)) or k in {'service','version'} and isinstance(v,str) and len(v)<80)} if isinstance(data,dict) else {}
        except (OSError,ValueError,http.client.HTTPException) as exc:entry['error_type']=type(exc).__name__
        finally:connection.close()
        health.append(entry)
    report['read_only_local_health']=health
    pairs=[('control/tampermonkey_multichat/command_router.py',Path.home()/'.local/share/prediction-chat-bridge/command_router.py'),('control/tampermonkey_multichat/prediction-chat-wake.user.js',Path.home()/'.local/share/prediction-chat-bridge/prediction-chat-wake.user.js')]
    for name in ['kalshi_weather_index_recorder.py','twc_hourly_recorder.py','market_reaction.py']:
        pairs.append(('control/weather/'+name,Path.home()/'prediction_research/control/weather'/name))
    report['deployment_file_comparison']=[]
    for canonical,installed in pairs:
        try:entry={'canonical':canonical,'installed':str(installed),'canonical_sha256':sha(ROOT/canonical),'installed_sha256':sha(installed)};entry['matches']=entry['canonical_sha256']==entry['installed_sha256']
        except OSError as exc:entry={'canonical':canonical,'installed':str(installed),'error_type':type(exc).__name__}
        report['deployment_file_comparison'].append(entry)
    state=Path.home()/'.local/state/prediction-research';report['receipts']=[]
    for name in ['prod-runtime-sync-latest.json','scheduled-cycle-latest.json','runtime-health-latest.json','git-checkpoint-latest.json']:
        p=state/name
        try:
            data=json.loads(p.read_text());entry={'name':name,'sha256':sha(p),'selected_fields':{k:data[k] for k in ['status','timestamp','timestamp_utc','run_id'] if k in data}}
            stamp=data.get('timestamp_utc',data.get('timestamp'))
            if stamp:entry['age_seconds']=(dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(stamp.replace('Z','+00:00'))).total_seconds()
        except (OSError,ValueError,TypeError,AttributeError) as exc:entry={'name':name,'error_type':type(exc).__name__}
        report['receipts'].append(entry)
    report['production_queue_counts']={name:len(list((ROOT/'control/tasks'/name).glob('*.json'))) for name in ['pending','running','completed','failed']}
    report['qualified_scope']={'offline_canonical_contracts':'PASS' if next(x for x in report['checks'] if x['label']=='offline_contracts').get('exit_code')==0 else 'SEE_CHECKS','temporary_loopback_and_persistent_rebind':'SEE_real_loopback','deployed_bridge_browser_e2e':'UNPROVEN','hourly_useful_work':'REQUIRES_RECEIPT_REVIEW','production_restart_reboot':'NOT_PERFORMED','deployed_code_loaded':'UNPROVEN_file_match_is_not_loaded_code_attestation'}
    report['finished_at']=dt.datetime.now(dt.timezone.utc).isoformat();save()
    (out/'README.md').write_text('# WSL kwalificatiebewijs\n\nRESULT.json en testlogs zijn de bewijsbron. Groene fixtures/health zijn geen productie-E2E-PASS. Geen diensten herstart, queue hervat, bridgebericht verzonden, externe API of handelsactie uitgevoerd. Tijdelijke server/pytest-resources opgeruimd. Beoordeel filedrift, receipts en daadwerkelijke geladen runtime afzonderlijk.\n')
    print('Evidence:',out)
    print('Geen productie-E2E-PASS afgegeven; laat RESULT.json en beide testlogs beoordelen.')
    return 0 if all(x.get('exit_code')==0 for x in report['checks'] if x['label'] in scopes) else 1

if __name__=='__main__':
    raise SystemExit(main())
