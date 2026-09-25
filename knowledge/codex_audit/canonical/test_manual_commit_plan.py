from pathlib import Path
import tempfile,subprocess,json,hashlib,shutil,datetime
real=Path('/home/leonh/prediction_research_prod');source=real/'knowledge/codex_audit/canonical';manifest=json.loads((source/'canonical_change_manifest.json').read_text())
h=lambda b:hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory(prefix='codex-commit-plan-test-') as tmp:
 r=Path(tmp)
 def git(*args):return subprocess.check_output(['git',*args],cwd=r,stderr=subprocess.STDOUT)
 git('init','-q');git('config','user.name','Audit fixture');git('config','user.email','audit@example.invalid')
 for row in manifest['paths']:
  name=row['path'];before=source/'before'/name
  if before.exists():
   p=r/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(before.read_bytes())
 router='control/tampermonkey_multichat/command_router.py'
 (r/router).write_bytes(subprocess.check_output(['git','show',manifest['source_commit']+':'+router],cwd=real))
 git('add','.');git('commit','-qm','fixture baseline');head=git('rev-parse','HEAD').decode().strip()
 (r/router).write_bytes((source/'before'/router).read_bytes());(r/'owner-note.txt').write_text('synthetic unrelated staged owner work\n');git('add','--',router,'owner-note.txt');index=h(git('diff','--cached','--binary'))
 for row in manifest['paths']:
  p=r/row['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((real/row['path']).read_bytes())
 d=r/'knowledge/codex_audit/canonical';d.mkdir(parents=True,exist_ok=True)
 shutil.copy2(source/'commit_locally.py',d/'commit_locally.py')
 m={**manifest,'source_commit':head};(d/'canonical_change_manifest.json').write_text(json.dumps(m));(d/'preflight.json').write_text(json.dumps({'index_diff_sha256':index}))
 proc=subprocess.run(['python3',str(d/'commit_locally.py')],capture_output=True,text=True)
 assert proc.returncode==0,proc.stderr
 assert git('status','--short').decode().strip()=='A  owner-note.txt'
 assert git('show','HEAD:'+router)==(real/router).read_bytes()
 assert int(git('rev-list','--count','HEAD'))==7
 (source/'commit_plan_test.json').write_text(json.dumps({'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':proc.returncode,'stdout':proc.stdout,'six_local_commits_created':True,'unrelated_staged_owner_file_preserved':True,'router_includes_preserved_owner_basis':True,'canonical_git_mutated':False,'temporary_fixture_cleaned_on_exit':True},indent=2)+'\n')
 print('Manual commit plan: six fixture commits, staged owner work preserved; no canonical Git writes')
