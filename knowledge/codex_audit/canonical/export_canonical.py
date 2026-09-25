"""Bewaar uitsluitend auditreparaties t.o.v. beschermde preflightbasis."""
from pathlib import Path
import hashlib,json,difflib,subprocess,datetime
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
h=lambda b:hashlib.sha256(b).hexdigest()
pre=json.loads((HERE/'preflight.json').read_text())
paths=[row['path'] for row in pre['paths']]+['control/tampermonkey_multichat/test_userscript_v046_guard_static.py','control/tampermonkey_multichat/test_userscript_delivery_dedupe_static.py','tests/bridge/test_tampermonkey_multichat.py']
paths+= [str(p.relative_to(ROOT)) for p in (ROOT/'tests/audit').glob('*.py')]
rows=[];diff=[]
for name in sorted(set(paths)):
    p=ROOT/name;before=HERE/'before'/name
    if not before.exists() and name in pre['tracked_hashes']:
        original=subprocess.check_output(['git','show',pre['head']+':'+name],cwd=ROOT)
        assert h(original)==pre['tracked_hashes'][name], 'Niet-triviale basis: '+name
        before.parent.mkdir(parents=True,exist_ok=True);before.write_bytes(original)
    original=before.read_bytes() if before.exists() else b''
    current=p.read_bytes()
    if original==current:continue
    diff.extend(difflib.unified_diff(original.decode().splitlines(True),current.decode().splitlines(True),fromfile='a/'+name if before.exists() else '/dev/null',tofile='b/'+name))
    rows.append({'path':name,'before_exists':before.exists(),'before_sha256':h(original),'canonical_sha256':h(current)})
(HERE/'canonical_changes.patch').write_text(''.join(diff))
index_hash=h(subprocess.check_output(['git','diff','--cached','--binary'],cwd=ROOT))
changed_unrelated=[]
for name,sha in pre['tracked_hashes'].items():
    if name in paths or name.startswith('knowledge/codex_audit/'):continue
    p=ROOT/name
    if not p.exists() or h(p.read_bytes())!=sha:changed_unrelated.append(name)
(HERE/'canonical_change_manifest.json').write_text(json.dumps({'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_commit':pre['head'],'patch_basis':'Preflightwerkboom inclusief staged routerwerk, niet kale HEAD.','index_unchanged':index_hash==pre['index_diff_sha256'],'unrelated_tracked_changes_since_preflight':changed_unrelated,'paths':rows},indent=2)+'\n')
assert index_hash==pre['index_diff_sha256'],'INDEX CHANGED'
assert not changed_unrelated,'UNRELATED CHANGES'
print('Canonical repairs:',len(rows),'; owner index and unrelated tracked files unchanged')
