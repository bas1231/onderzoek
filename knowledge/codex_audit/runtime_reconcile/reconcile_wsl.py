#!/usr/bin/env python3
"""Vijf begrensde bronupdates; geen hourly/queue, Gitmutatie, API of handel."""
import datetime, hashlib, json, os, pathlib, subprocess, tempfile, uuid
from test_payload import run
if not __debug__:
    raise RuntimeError("STOP: Python-optimalisatie schakelt veiligheidsasserties uit")
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def command(args):
    return subprocess.run(args,text=True,capture_output=True,timeout=30,check=True).stdout.strip()
def main():
    manifest=json.loads((HERE/'preservation_manifest.json').read_text())
    out=HERE/'external_runs'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]);out.mkdir(parents=True)
    result={'status':'STARTED','runtime_e2e':'UNPROVEN','scientific_status':'NO_PROVEN_EDGE','changes':[]}
    def save():(out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        # Geen productiejob importeren/uitvoeren: alleen allowlistbestanden en synthetische tests.
        assert len(manifest['paths'])==5
        expected=['control/tampermonkey_multichat/command_router.py','control/weather/kalshi_weather_index_recorder.py','control/weather/twc_hourly_recorder.py','control/weather/market_reaction.py','control/jobs/evaluate_kwi_full_station_checkpoint_e369.py']
        assert [x['source'] for x in manifest['paths']]==expected
        indices=[ROOT/'.git/index',pathlib.Path.home()/'prediction_research/.git/index']
        index_before={str(p):sha(p) for p in indices}
        owner_before={p:sha(ROOT/p) for p in manifest['owner_work']}
        for p,value in manifest['owner_work'].items():assert owner_before[p]==value,'Ownerwerk gewijzigd sinds analyse: '+p
        assert index_before[str(indices[0])]==manifest['index_sha256'],'Canonical index gewijzigd sinds analyse'
        unit=pathlib.Path.home()/'.config/systemd/user/prediction-chat-router.service'
        assert sha(unit)==json.loads((HERE/'unit_manifest.json').read_text())['router_unit_sha256'],'Routerunit gewijzigd'
        assert not command(['systemctl','--user','show','prediction-chat-router.service','--property=DropInPaths','--value']),'Niet-beoordeelde drop-in'
        for row in manifest['paths']:
            target=pathlib.Path(row['target'])
            expected_target=pathlib.Path.home()/('.local/share/prediction-chat-bridge/command_router.py' if row['source']==expected[0] else 'prediction_research/'+row['source'])
            assert target==expected_target and not target.is_symlink()
            assert sha(ROOT/row['source'])==row['after_sha256'],'Canonical bron gewijzigd'
            assert sha(HERE/'payload'/row['source'])==row['after_sha256'],'Payload gewijzigd'
            assert sha(target) in (row['before_sha256'],row['after_sha256']),'Ownerconflict: '+str(target)
        # Eerst tests met exact de payload, inclusief echte tijdelijke sockets; geen productie-POST.
        assert run(out/'tests',sockets=True)==0,'Payloadregressie faalt; niets uitgerold'
        for row in manifest['paths']:
            target=pathlib.Path(row['target']);current=sha(target)
            if current==row['after_sha256']:continue
            assert current==row['before_sha256'],'Concurrente bronwijziging: '+str(target)
            backup=out/'before'/row['source'];backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(target.read_bytes())
            st=target.stat();assert st.st_uid==os.getuid(),'Niet eigen bestand'
            name=None
            try:
                with tempfile.NamedTemporaryFile(dir=target.parent,prefix='.audit-reconcile-',delete=False) as f:
                    name=f.name;os.fchmod(f.fileno(),st.st_mode & 0o777);os.fchown(f.fileno(),st.st_uid,st.st_gid)
                    f.write((HERE/'payload'/row['source']).read_bytes());f.flush();os.fsync(f.fileno())
                assert sha(target)==row['before_sha256'],'Concurrente wijziging vóór vervanging'
                os.replace(name,target);name=None
                result['changes'].append({'target':str(target),'sha256':sha(target)});save()
            finally:
                if name is not None:os.unlink(name)
        assert all(sha(pathlib.Path(x['target']))==x['after_sha256'] for x in manifest['paths'])
        assert all(sha(pathlib.Path(p))==h for p,h in index_before.items()),'Index veranderde tijdens uitvoering'
        assert all(sha(ROOT/p)==h for p,h in owner_before.items()),'Ownerwerk veranderde tijdens uitvoering'
        # Alleen de beoordeelde lokale router herladen. Geen timer/collector/executor/hourly starten.
        command(['systemctl','--user','try-restart','prediction-chat-router.service'])
        result['systemd']=command(['systemctl','--user','show','prediction-chat-router.service','prediction-research-hourly-director.service','--property=Id,ActiveState,SubState,MainPID,ExecMainStatus,Result','--no-pager'])
        result['status']='DEPLOYED_SOURCE_VERIFIED'
        result['limits']=['Hourly blijft door ownerindex/no-push geblokkeerd; niet gestart','Weatherprocessen niet herstart: nieuwe invocaties laden bron; bestaande imports niet geattesteerd','Router try-restart bewijst geen browser/Director E2E','Geen userscript gewijzigd']
        result['preservation']='Beide indices en vastgelegde ownerbestanden ongewijzigd'
    except Exception as exc:
        result['status']='BLOCKED_OR_PARTIAL';result['error_type']=type(exc).__name__;result['error']=str(exc)[:500]
        # Geen automatische rollback die later ownerwerk kan overschrijven.
    finally:save();print('Bewijs:',out);print('Status:',result['status'],'; productie-E2E blijft UNPROVEN')
    return 0 if result['status']=='DEPLOYED_SOURCE_VERIFIED' else 1
if __name__=='__main__':raise SystemExit(main())
