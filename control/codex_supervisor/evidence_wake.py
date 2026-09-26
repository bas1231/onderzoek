"""Fail-closed deterministic candidate wake from typed local evidence."""
import datetime as dt
import hashlib
import importlib.util
import json
import pathlib
import re

P = pathlib.Path
CONDITION_SCHEMA = 'PVA_EVIDENCE_WAKE_CONDITION_V1'
EVIDENCE_SCHEMA = 'PVA_CANDIDATE_EVIDENCE_V1'
ROOTS = ('knowledge/evidence/candidate_events', 'knowledge/experiment_results')
WAIT_STATES = {'WAITING_FOR_DATA', 'WAITING_FOR_RESULT', 'RUNNING', 'PARKED', 'WATCH', 'REJECT', 'CLOSED_NEGATIVE', 'NEEDS_REVISION'}
MAX_BYTES = 262144


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _time(value):
    if not isinstance(value, str):
        raise ValueError('INVALID_EVIDENCE_TIMESTAMP')
    parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('NAIVE_EVIDENCE_TIMESTAMP')
    return parsed.astimezone(dt.timezone.utc)


def _condition(value):
    if not isinstance(value, dict) or value.get('schema') != CONDITION_SCHEMA:
        raise ValueError('UNSTRUCTURED_WAKE_CONDITION')
    allowed = {'schema', 'evidence_kinds', 'experiment_id', 'minimum_scorable_pairs', 'minimum_groups', 'minimum_scorable_pairs_per_group', 'minimum_full_fills', 'required_status', 'require_conservative_proof', 'required_hash_fields', 'protocol_ref', 'cutoff'}
    if set(value) - allowed:
        raise ValueError('UNKNOWN_WAKE_CONDITION_FIELD')
    kinds = value.get('evidence_kinds')
    if not isinstance(kinds, list) or not kinds or any(not isinstance(x, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,63}', x) for x in kinds):
        raise ValueError('INVALID_WAKE_EVIDENCE_KINDS')
    for key in ('minimum_scorable_pairs', 'minimum_groups', 'minimum_scorable_pairs_per_group', 'minimum_full_fills'):
        if key in value and (type(value[key]) is not int or value[key] < 1):
            raise ValueError('INVALID_WAKE_THRESHOLD')
    for key in ('experiment_id', 'required_status', 'protocol_ref'):
        if key in value and (not isinstance(value[key], str) or not value[key]):
            raise ValueError('INVALID_WAKE_BINDING')
    if 'require_conservative_proof' in value and type(value['require_conservative_proof']) is not bool:
        raise ValueError('INVALID_WAKE_PROOF_FLAG')
    if 'required_hash_fields' in value and (not isinstance(value['required_hash_fields'],list) or any(not isinstance(x,str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,63}',x) for x in value['required_hash_fields'])):
        raise ValueError('INVALID_REQUIRED_HASH_FIELDS')
    if 'cutoff' in value:_time(value['cutoff'])
    return value


def _condition_for(overlay):
    state = overlay.get('queue_status')
    value = overlay.get('resurrection_condition') if state in {'PARKED', 'REJECT', 'CLOSED_NEGATIVE', 'NEEDS_REVISION'} else overlay.get('wake_condition')
    return _condition(value) if isinstance(value, dict) else None


def _read_evidence(repo, ref):
    rel = P(ref)
    if rel.is_absolute() or '..' in rel.parts or rel.suffix.lower() != '.json' or not any(rel.as_posix().startswith(root + '/') for root in ROOTS):
        raise ValueError('UNSAFE_EVIDENCE_REF')
    path, cursor = repo / rel, repo
    for part in rel.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError('EVIDENCE_SYMLINK')
    if not path.is_file():
        raise ValueError('EVIDENCE_MISSING')
    raw = path.read_bytes()
    if len(raw) > MAX_BYTES:
        raise ValueError('EVIDENCE_TOO_LARGE')
    doc = json.loads(raw)
    required = {'schema', 'evidence_id', 'candidate_id', 'evidence_kind', 'status', 'evidence_timestamp', 'available_at', 'archived_at', 'backfill', 'source_manifest_ref', 'source_manifest_sha256'}
    if not isinstance(doc, dict) or doc.get('schema') != EVIDENCE_SCHEMA or not required <= doc.keys() or type(doc['backfill']) is not bool:
        raise ValueError('MALFORMED_EVIDENCE')
    if any(not isinstance(doc[k], str) or not doc[k] for k in ('evidence_id', 'candidate_id', 'evidence_kind', 'status')):
        raise ValueError('MALFORMED_EVIDENCE')
    evidence_time, available, archived = map(_time, (doc['evidence_timestamp'], doc['available_at'], doc['archived_at']))
    if doc['backfill'] or evidence_time > available or available > archived or archived > dt.datetime.now(dt.timezone.utc):
        raise ValueError('EVIDENCE_CHRONOLOGY_INVALID')
    manifest_ref=doc['source_manifest_ref'];manifest_hash=doc['source_manifest_sha256']
    if not isinstance(manifest_ref,str) or not re.fullmatch(r'[0-9a-f]{64}',str(manifest_hash)):
        raise ValueError('EVIDENCE_MANIFEST_PROVENANCE_MISSING')
    manifest_path,manifest,manifest_raw,_,retrieved,manifest_archived=_read_manifest(repo,manifest_ref)
    if sha(manifest_raw)!=manifest_hash or manifest.get('backfill') is not False or retrieved>manifest_archived or manifest_archived>available or manifest_archived>archived:
        raise ValueError('EVIDENCE_MANIFEST_PROVENANCE_INVALID')
    return path, doc, raw, evidence_time, available, archived, manifest_path, manifest, manifest_raw


def _read_manifest(repo,ref):
    rel=P(ref)
    if rel.is_absolute() or '..' in rel.parts or not rel.as_posix().startswith('knowledge/evidence/manifests/'):
        raise ValueError('UNSAFE_EVIDENCE_MANIFEST_REF')
    path,cursor=repo/rel,repo
    for part in rel.parts:
        cursor=cursor/part
        if cursor.is_symlink():raise ValueError('EVIDENCE_MANIFEST_SYMLINK')
    raw=path.read_bytes()
    if len(raw)>MAX_BYTES:raise ValueError('EVIDENCE_MANIFEST_TOO_LARGE')
    manifest=json.loads(raw)
    required={'schema','source_ref','source_sha256','retrieved_at','archived_at','backfill'}
    if not isinstance(manifest,dict) or manifest.get('schema')!='PVA_IMMUTABLE_EVIDENCE_MANIFEST_V1' or not required<=manifest.keys():
        raise ValueError('MALFORMED_EVIDENCE_MANIFEST')
    if not isinstance(manifest['source_ref'],str) or not manifest['source_ref'] or not re.fullmatch(r'[0-9a-f]{64}',str(manifest['source_sha256'])):
        raise ValueError('INVALID_EVIDENCE_MANIFEST_SOURCE')
    retrieved,archived=map(_time,(manifest['retrieved_at'],manifest['archived_at']))
    if type(manifest['backfill']) is not bool or archived>dt.datetime.now(dt.timezone.utc):raise ValueError('EVIDENCE_MANIFEST_CHRONOLOGY_INVALID')
    return path,manifest,raw,None,retrieved,archived


def _matches(condition, doc, available, cutoff):
    if available <= cutoff or doc.get('evidence_kind') not in condition['evidence_kinds']:
        return False
    if condition.get('required_status') and doc.get('status') != condition['required_status']:
        return False
    if condition.get('experiment_id') and doc.get('experiment_id') != condition['experiment_id']:
        return False
    for key, field in (('minimum_scorable_pairs', 'scorable_pairs'), ('minimum_full_fills', 'conservative_full_fills')):
        if key in condition and (type(doc.get(field)) is not int or doc[field] < condition[key]):
            return False
    if 'minimum_groups' in condition or 'minimum_scorable_pairs_per_group' in condition:
        grouped=doc.get('scorable_pairs_by_group')
        if not isinstance(grouped,dict) or any(type(n) is not int or n<0 for n in grouped.values()):return False
        threshold=condition.get('minimum_scorable_pairs_per_group',1)
        qualifying=sum(n>=threshold for n in grouped.values())
        if qualifying<condition.get('minimum_groups',1):return False
    for field in condition.get('required_hash_fields',[]):
        if not isinstance(doc.get(field),str) or not re.fullmatch(r'[0-9a-f]{64}',doc[field]):return False
    if condition.get('require_conservative_proof') and doc.get('conservative_proof') is not True:
        return False
    if condition.get('protocol_ref') and (doc.get('protocol_ref') != condition['protocol_ref'] or doc.get('protocol_sha256') == doc.get('prior_protocol_sha256')):
        return False
    return True


def _latest_overlays(root):
    latest, folder = {}, root / 'candidate_states'
    if not folder.exists():
        return latest
    for path in sorted(folder.glob('*.json')):
        if path.is_symlink():
            raise ValueError('CANDIDATE_OVERLAY_SYMLINK')
        item, cid = json.loads(path.read_text()), None
        cid = item.get('candidate_id')
        if cid:
            stamp=float(item.get('decision_timestamp',0))
            prior=latest.get(cid)
            if prior is None or stamp>float(prior[1].get('decision_timestamp',0)):
                latest[cid]=(path,item)
            elif stamp==float(prior[1].get('decision_timestamp',0)) and item.get('originating_task_id')!=prior[1].get('originating_task_id'):
                raise ValueError('AMBIGUOUS_CANDIDATE_OVERLAY_ORDER')
    return latest


def register_waiting_candidates(supervisor,repo):
    """Persist read-only registrations for source candidates with typed gates."""
    repo,root=P(repo),P(supervisor.root);folder=repo/'knowledge/candidates'
    if not folder.exists():return
    for path in sorted(folder.glob('*.json')):
        if path.is_symlink():raise ValueError('CANDIDATE_SYMLINK')
        raw=path.read_bytes();candidate=json.loads(raw);cid=candidate.get('candidate_id');state=candidate.get('queue_status')
        if not isinstance(cid,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',cid) or state not in WAIT_STATES:continue
        if any(candidate.get(k) is not False for k in ('live_trading','paid_actions','wallet_actions')):continue
        if any(candidate.get(k) for k in ('human_gate','requires_human_approval','requires_approval','financial_gate','live_execution_required')):continue
        condition_value=candidate.get('resurrection_condition') if state in {'PARKED','REJECT','CLOSED_NEGATIVE','NEEDS_REVISION'} else candidate.get('evidence_wake_condition') or candidate.get('resume_condition')
        if not isinstance(condition_value,dict):continue
        condition=_condition(condition_value)
        cutoff_value=condition.get('cutoff') or candidate.get('prospective_cutoff')
        if not isinstance(cutoff_value,str):continue
        cutoff=_time(cutoff_value)
        refs=[]
        if candidate.get('manual_seed_ref'):refs.append(candidate['manual_seed_ref'])
        for key in ('prospective_protocols','evidence_refs'):
            value=candidate.get(key,[])
            if not isinstance(value,list) or any(not isinstance(x,str) for x in value):raise ValueError('MALFORMED_EVIDENCE_REFS')
            refs.extend(value)
        source_hashes={path.relative_to(repo).as_posix():sha(raw)};referenced={}
        for ref in sorted(set(refs)):
            src,_,body=_read_source(repo,ref)
            if len(body)>MAX_BYTES:raise ValueError('EVIDENCE_TOO_LARGE')
            source_hashes[ref]=sha(body);referenced[ref]=body.decode('utf-8')
        substantive={k:v for k,v in candidate.items() if k not in {'updated_at','created_at','queue_entered_at','priority'}}
        version=sha(json.dumps({'candidate':substantive,'evidence':{k:v for k,v in source_hashes.items() if k!=path.relative_to(repo).as_posix()},'condition':condition},sort_keys=True).encode())
        overlay_path=root/'candidate_states'/(sha(cid.encode())[:16]+'-'+version[:32]+'.json')
        if overlay_path.exists():continue
        if sha(path.read_bytes())!=source_hashes[path.relative_to(repo).as_posix()]:raise ValueError('CANDIDATE_CHANGED_DURING_REGISTRATION')
        now=dt.datetime.now(dt.timezone.utc).timestamp()
        overlay={'candidate_id':cid,'source_hashes':source_hashes,'decision_timestamp':now,'wait_cutoff':cutoff.isoformat(),
                 'queue_status':state,'finding':'Bronstatus geregistreerd; wacht op getypeerde, nieuwe evidence.','next_action':'Wacht op evidence die exact aan de vastgelegde conditie voldoet.',
                 'scientific_status':'NO_PROVEN_EDGE','originating_task_id':'WAIT-REGISTRATION-'+version[:32],
                 'completion_hash':None,'evidence_refs':sorted(source_hashes),'applied_version':version,
                 'candidate_snapshot':candidate,'referenced_evidence':referenced,
                 'wake_condition':condition if state not in {'PARKED','REJECT','CLOSED_NEGATIVE','NEEDS_REVISION'} else None,
                 'resurrection_condition':condition if state in {'PARKED','REJECT','CLOSED_NEGATIVE','NEEDS_REVISION'} else candidate.get('resurrection_condition'),
                 'registration_only':True,'live_trading':False,'paid_actions':False,'wallet_actions':False,'remote_push':False}
        from supervisor import atomic
        atomic(overlay_path,overlay)
        print(json.dumps({'event':'CANDIDATE_WAIT_REGISTERED','candidate_id':cid,'source_hash':source_hashes[path.relative_to(repo).as_posix()],'state':state}),flush=True)


def select_task(supervisor, repo):
    """Write/recover one idempotent wake record, then return its review task."""
    repo, root = P(repo), P(supervisor.root)
    register_waiting_candidates(supervisor,repo)
    artifacts = []
    for base in ROOTS:
        folder = repo / base
        if folder.exists():
            if folder.is_symlink():
                raise ValueError('EVIDENCE_ROOT_SYMLINK')
            artifacts.extend(sorted(folder.rglob('*.json')))
    policy_spec=importlib.util.spec_from_file_location('wake_candidate_queue_policy',P(__file__).parents[1]/'hourly/candidate_queue.py')
    policy=importlib.util.module_from_spec(policy_spec);policy_spec.loader.exec_module(policy);policy.ROOT=repo;policy.CANDIDATES=repo/'knowledge/candidates'
    ordered=sorted(_latest_overlays(root).values(),key=lambda pair:policy.effective_priority(pair[1].get('candidate_snapshot',{})))
    for overlay_path, overlay in ordered:
        cid, state = overlay.get('candidate_id'), overlay.get('queue_status')
        if state not in WAIT_STATES:
            continue
        condition = _condition_for(overlay)
        if condition is None:
            continue
        raw_cutoff=overlay.get('wait_cutoff') or overlay['decision_timestamp']
        cutoff=dt.datetime.fromtimestamp(float(raw_cutoff),dt.timezone.utc) if isinstance(raw_cutoff,(int,float)) else _time(raw_cutoff)
        condition_hash = sha(json.dumps(condition, sort_keys=True, separators=(',', ':')).encode())
        for artifact in artifacts:
            ref = artifact.relative_to(repo).as_posix()
            path, doc, raw, evidence_time, available, archived, manifest_path, manifest, manifest_raw = _read_evidence(repo, ref)
            if doc['candidate_id'] != cid:
                continue
            print(json.dumps({'event':'EVIDENCE_DISCOVERED','candidate_id':cid,'evidence_ref':ref,'evidence_sha256':sha(raw)}),flush=True)
            if not _matches(condition, doc, available, cutoff):
                print(json.dumps({'event':'NO_MATCH','candidate_id':cid,'evidence_ref':ref}),flush=True)
                continue
            evidence_hash = sha(raw)
            dedupe = sha(f'{cid}\0{condition_hash}\0{evidence_hash}'.encode())
            task_id = 'CANDIDATE-WAKE-' + dedupe[:40]
            wake_path = root / 'candidate_wakes' / f'{dedupe}.json'
            wake = {
                'candidate_id': cid, 'previous_overlay': str(overlay_path.relative_to(root)),
                'previous_overlay_sha256': sha(overlay_path.read_bytes()), 'previous_state': state,
                'wake_reason': 'STRUCTURED_POST_CUTOFF_EVIDENCE_MATCH', 'resume_condition': condition,
                'resurrection_condition': overlay.get('resurrection_condition'), 'evidence_refs': [ref],
                'evidence_sha256': evidence_hash, 'evidence_timestamp': evidence_time.isoformat(),
                'evidence_available_at': available.isoformat(), 'candidate_cutoff': cutoff.isoformat(),
                'wake_timestamp': dt.datetime.now(dt.timezone.utc).isoformat(), 'new_candidate_version': dedupe,
                'review_task_id': task_id, 'dedupe_key': dedupe, 'scientific_status': 'NO_PROVEN_EDGE',
            }
            from supervisor import atomic
            if wake_path.exists():
                saved = json.loads(wake_path.read_text())
                if saved.get('evidence_sha256') != evidence_hash or saved.get('dedupe_key') != dedupe:
                    raise ValueError('WAKE_RECORD_CONFLICT')
                wake = saved
            else:
                atomic(wake_path, wake)
            if supervisor.db.execute('select 1 from tasks where id=?', (task_id,)).fetchone():
                continue
            candidate = overlay.get('candidate_snapshot')
            if not isinstance(candidate, dict) or candidate.get('candidate_id') != cid:
                raise ValueError('WAKE_CANDIDATE_SNAPSHOT_MISSING')
            if sha(overlay_path.read_bytes()) != wake['previous_overlay_sha256']:
                raise ValueError('WAKE_OVERLAY_CHANGED')
            original_hashes=overlay.get('source_hashes',{})
            old_refs=overlay.get('referenced_evidence',{})
            if not isinstance(original_hashes,dict) or not isinstance(old_refs,dict):
                raise ValueError('WAKE_SOURCE_PROVENANCE_MISSING')
            for old_ref,expected in original_hashes.items():
                old_path,old_doc,old_raw,*_= _read_source(repo,old_ref)
                if sha(old_raw)!=expected:raise ValueError('WAKE_SOURCE_CHANGED')
            manifest_ref=doc['source_manifest_ref']
            hashes={**original_hashes,ref:evidence_hash,manifest_ref:sha(manifest_raw)}
            refs={**old_refs,ref:raw.decode('utf-8'),manifest_ref:manifest_raw.decode('utf-8')}
            prompt = ('Herbeoordeel de kandidaat met de exacte oude overlay en alleen de gehashte nieuwe gestructureerde evidence plus het hash-gebonden immutable bronmanifest. Deterministische wake; modeltekst bepaalt geen trigger. Geen tools, code of economische promotie. Retourneer uitsluitend het gestructureerde candidate-resultaat; scientific_status=NO_PROVEN_EDGE.\n' + json.dumps({'candidate': candidate, 'previous_overlay': overlay, 'wake_record': wake, 'new_evidence': {ref: raw.decode('utf-8'),manifest_ref:manifest_raw.decode('utf-8')}}, ensure_ascii=False, sort_keys=True))
            if len(prompt) > 100000:
                raise ValueError('WAKE_PROMPT_TOO_LARGE')
            print(json.dumps({'event': 'EVIDENCE_MATCHED', 'candidate_id': cid, 'evidence_ref': ref, 'evidence_sha256': evidence_hash}), flush=True)
            print(json.dumps({'event': 'CANDIDATE_WAKE_RECORDED', 'candidate_id': cid, 'task_id': task_id, 'evidence_sha256': evidence_hash}), flush=True)
            print(json.dumps({'event': 'NEXT_TASK_SELECTED', 'candidate_id': cid, 'task_id': task_id, 'wake_dedupe_key': dedupe}), flush=True)
            return {'task_id': task_id, 'candidate_id': cid, 'candidate_dispatch': True, 'candidate_wake': True,
                    'wake_record_ref': str(wake_path.relative_to(root)), 'wake_record_sha256': sha(wake_path.read_bytes()), 'candidate_runtime_root': str(root), 'candidate_source_root': str(repo),
                    'candidate_source_hashes': hashes, 'candidate_snapshot': candidate,
                    'wake_condition': condition, 'wake_record': wake, 'referenced_evidence': refs,
                    'task_class': 'research_review', 'priority': 100, 'expected_value': 5,
                    'estimated_reasoning_cost': 1, 'created_at': wake['wake_timestamp'], 'prompt': prompt,
                    'input_sha256': sha(prompt.encode())}
    return None


def _read_source(repo, ref):
    rel=P(ref)
    allowed=('knowledge/candidates','knowledge/manual_scout_seeds','knowledge/evidence','knowledge/research_os','knowledge/experiment_results')
    if rel.is_absolute() or '..' in rel.parts or not any(rel.as_posix().startswith(x+'/') for x in allowed):
        raise ValueError('WAKE_SOURCE_REF_UNSAFE')
    path,cursor=repo/rel,repo
    for part in rel.parts:
        cursor=cursor/part
        if cursor.is_symlink():raise ValueError('WAKE_SOURCE_SYMLINK')
    raw=path.read_bytes()
    return path,None,raw
