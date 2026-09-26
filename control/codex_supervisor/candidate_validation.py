"""Enige bounded build/validatieroute: vooraf vastgelegde pure shadow-deathchecks."""
import hashlib,json,pathlib,subprocess,sys,datetime,os
P=pathlib.Path

def run(task,repo,folder):
    root=P(task['overlay_path']).resolve();body=root.read_bytes()
    if hashlib.sha256(body).hexdigest()!=task['overlay_sha256']:raise ValueError('OVERLAY_CHANGED')
    overlay=json.loads(body);dbtask=json.loads(task['prompt'])
    if dbtask.get('operation')!='PROTOCOL_DEATHCHECK_VALIDATION' or overlay['candidate_id']!=task['candidate_id']:raise ValueError('LOCAL_OPERATION_NOT_ALLOWLISTED')
    evidence=overlay['referenced_evidence'];candidate=overlay['candidate_snapshot'];refs=overlay['build_handoff']['protocol_refs']
    for name,expected in overlay['build_handoff']['implementation_hashes'].items():
        if hashlib.sha256((P(repo)/name).read_bytes()).hexdigest()!=expected:raise ValueError('VALIDATION_IMPLEMENTATION_CHANGED')
    if dbtask.get('implementation_hashes')!=overlay['build_handoff']['implementation_hashes']:raise ValueError('VALIDATION_TASK_PROVENANCE_MISMATCH')
    if not refs:raise ValueError('NO_PROTOCOL')
    if overlay['source_hashes']!=dbtask.get('source_hashes') or refs!=dbtask.get('protocol_refs') or plan_hashes(overlay)!=dbtask.get('implementation_hashes'):raise ValueError('SOURCE_MANIFEST_MISMATCH')
    for ref,expected in overlay['source_hashes'].items():
        p=P(repo)/ref
        if p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:raise ValueError('SOURCE_CHANGED_BEFORE_VALIDATION')
    result_path=P(folder)/'CANDIDATE_VALIDATION.json'
    if result_path.exists():report=json.loads(result_path.read_text())
    else:
        from shadow_protocol import run_deathchecks
        reports=[]
        env={'PATH':os.environ.get('PATH','/usr/bin:/bin'),'HOME':str(P(folder).resolve()),'PYTHONDONTWRITEBYTECODE':'1'}
        head=subprocess.run(['git','rev-parse','HEAD'],cwd=repo,text=True,capture_output=True,check=True).stdout.strip()
        code_hashes={name:hashlib.sha256((P(repo)/name).read_bytes()).hexdigest() for name in overlay['build_handoff']['implementation_hashes']}
        for ref in refs:
            doc=json.loads(evidence[ref]);expected_hash=overlay['source_hashes'][ref]
            for i in range(1,4):
                proc=subprocess.run([sys.executable,'-m','pytest','-q','tests/codex_supervisor/test_shadow_protocol.py'],cwd=repo,env=env,capture_output=True,text=True,timeout=120)
                checks=run_deathchecks(candidate,doc,overlay['source_hashes'],head)
                reports.append({'run':i,'protocol_ref':ref,'protocol_hash':expected_hash,'pytest_exit_code':proc.returncode,'pytest_stdout':proc.stdout,'pytest_stderr':proc.stderr,'result':checks})
                if proc.returncode:break
        # Recheck every pinned input after subprocess/tests: mutation during validation is a hard failure.
        for name,expected in overlay['build_handoff']['implementation_hashes'].items():
            if hashlib.sha256((P(repo)/name).read_bytes()).hexdigest()!=expected:raise ValueError('VALIDATION_IMPLEMENTATION_CHANGED_DURING_RUN')
        for ref,expected in overlay['source_hashes'].items():
            p=P(repo)/ref
            if p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:raise ValueError('SOURCE_CHANGED_DURING_VALIDATION')
        required_runs=3*len(refs)
        passed=len(reports)==required_runs and all(x['pytest_exit_code']==0 and x['result']['all_deathchecks_pass'] and x['result']['miami_regression_fixture']['pass'] for x in reports)
        report={'task_id':task['task_id'],'candidate_id':task['candidate_id'],'status':'PASS' if passed else 'FAIL','runs':reports,'required_runs':required_runs,'local_test_runs':len(reports),'local_test_runs_passed':sum(bool(x['result']['checks_pass'] and x['pytest_exit_code']==0) for x in reports),'prospective_runs':0,'prospective_clean_runs':0,'prospective_evidence':False,'source_code_commit':head,'working_tree_code_hashes':code_hashes,'test_command':[sys.executable,'-m','pytest','-q','-p','no:cacheprovider','tests/codex_supervisor/test_shadow_protocol.py'],'activation_authorized':False,'activation_blockers':['NO_READ_ONLY_RAW_ORDERBOOK_SEQUENCE_COLLECTOR','NO_PROSPECTIVE_RUNS'],'safety':{'live_trading':False,'paid_actions':False,'wallet_actions':False,'remote_push':False,'scientific_status':'NO_PROVEN_EDGE'}}
        from supervisor import atomic
        atomic(result_path,report)
    if report.get('task_id')!=task['task_id'] or report.get('candidate_id')!=task['candidate_id'] or report.get('status')!='PASS' or report.get('required_runs')!=3*len(refs) or report.get('local_test_runs')!=report.get('required_runs') or report.get('local_test_runs_passed')!=report.get('required_runs') or report.get('prospective_runs')!=0 or report.get('prospective_clean_runs')!=0:raise ValueError('VALIDATION_REPORT_FAILED')
    if report.get('candidate_id')!=task['candidate_id'] or report.get('prospective_evidence') is not False or report.get('activation_authorized') is not False or report.get('safety')!={'live_trading':False,'paid_actions':False,'wallet_actions':False,'remote_push':False,'scientific_status':'NO_PROVEN_EDGE'}:raise ValueError('VALIDATION_REPORT_UNSAFE')
    return report

def plan_hashes(overlay):
    return overlay.get('build_handoff',{}).get('implementation_hashes')
