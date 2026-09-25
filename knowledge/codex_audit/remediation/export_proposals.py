from pathlib import Path
import json,difflib,hashlib,datetime
r=Path('/home/leonh/prediction_research_prod'); f=Path('/tmp/codex-remediation-80a5ff7'); d=r/'knowledge/codex_audit/remediation'
charter=json.loads((d/'CHARTER.json').read_text())
paths=charter['planned_paths']+['control/policy_check.py','control/policy.json','tests/audit/test_reliability_regressions.py','tests/edge_hunter/test_warrant_issuer.py','tests/hourly/test_research_os_six_domain_e007.py','control/weather/test_market_reaction.py','control/weather/test_market_reaction_ws.py','control/tampermonkey_multichat/test_patch_v045_task_dedupe_static.py','knowledge/codex_audit/evidence/reproduce_defects.py']
manifest=[]; patch=[]
for name in paths:
    original=(r/name).read_bytes() if (r/name).exists() else b''
    proposed=(f/name).read_bytes()
    h=lambda b:hashlib.sha256(b).hexdigest()
    if name in charter['source_hashes']:
        assert h(original)==charter['source_hashes'][name],name
    target=d/'proposed'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(proposed)
    patch.extend(difflib.unified_diff(original.decode().splitlines(True),proposed.decode().splitlines(True),fromfile='a/'+name if (r/name).exists() else '/dev/null',tofile='b/'+name))
    manifest.append({'path':name,'base_exists':(r/name).exists(),'base_sha256':h(original),'proposed_sha256':h(proposed)})
(d/'prepared_latest.patch').write_text(''.join(patch));(d/'proposal_manifest.json').write_text(json.dumps({'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'production_modified':False,'paths':manifest},indent=2)+'\n')
print('Exported',len(paths),'files; original source hashes unchanged')
