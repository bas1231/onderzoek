from pathlib import Path
import json
import sys
import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'control/codex_supervisor'))

import supervisor as smod
import model_quality_gate as q
import astra_autonomous_review as ar


def overlay(qualification_fixture=False):
    return {
        "candidate_id":"AUTO-CANARY",
        "queue_status":"ASTRA_PREBUILD_REVIEW",
        "source_hashes":{"knowledge/candidates/AUTO-CANARY.json":"a"*64},
        "originating_task_id":"CANDIDATE-AUTO-CANARY-v1",
        "completion_hash":"b"*64,
        "validation_hash":None,
        "finding":"A bounded checker is worth falsifying.",
        "next_action":"Build only after independent review.",
        "candidate_snapshot":{
            "candidate_id":"AUTO-CANARY",
            "qualification_fixture":qualification_fixture,
            "prospective_protocols":[],
        },
        "qualification_fixture":qualification_fixture,
        "referenced_evidence":{"knowledge/evidence/x.json":"{}"},
        "scientific_status":"NO_PROVEN_EDGE",
        "decision_timestamp":1000,
        "live_trading":False,
        "paid_actions":False,
        "wallet_actions":False,
    }


def prepare(tmp_path,item=None):
    item=item or overlay()
    runtime=tmp_path/'runtime'
    states=runtime/'candidate_states'
    states.mkdir(parents=True)
    path=states/'candidate.json'
    path.write_text(json.dumps(item))
    repo=tmp_path/'repo'
    repo.mkdir()
    sup=smod.Supervisor(runtime,worker=lambda *args:0)
    return repo,sup,path,item


def test_select_task_requires_autonomous_astra_policy(tmp_path):
    repo,sup,path,item=prepare(tmp_path)
    with sup.locked():
        task=ar.select_task(sup,repo,path,item,'PREBUILD')
    assert task['astra_review_task'] is True
    assert task['model_policy']=='ASTRA_EXACT'
    assert task['candidate_id']=='AUTO-CANARY'
    assert task['binding_sha256']==q.review_binding(item,'PREBUILD')
    assert task['review_ref']==q.expected_review_ref(item,'PREBUILD')
    assert task['provenance_ref']==q.expected_autonomous_provenance_ref(item,'PREBUILD')
    assert task['live_trading'] is False


def test_autonomous_reviewer_rejects_qualification_fixture(tmp_path):
    repo,sup,path,item=prepare(tmp_path,overlay(qualification_fixture=True))
    with sup.locked(),pytest.raises(ar.AstraAutonomousReviewError,match='NOT_FOR_QUALIFICATION'):
        ar.select_task(sup,repo,path,item,'PREBUILD')


def test_worker_record_materializes_valid_autonomous_review(tmp_path):
    repo,sup,path,item=prepare(tmp_path)
    with sup.locked():
        task=ar.select_task(sup,repo,path,item,'PREBUILD')
    folder=sup.root/'runs'/'astra-test'
    folder.mkdir(parents=True)
    worker={
        "pid":123,
        "model":"gpt-6-astra-fixture",
        "model_selection":{
            "policy":"ASTRA_EXACT",
            "visible_astra_count":1,
            "selected_slug":"gpt-6-astra-fixture",
            "display_name":"GPT-6 Astra",
            "priority":1,
        },
        "thread_id":None,
        "started_at":1000,
        "command_flags":["exec","-m","gpt-6-astra-fixture"],
    }
    (folder/'WORKER.json').write_text(json.dumps(worker))
    final=json.dumps({
        "candidate_id":"AUTO-CANARY",
        "phase":"PREBUILD",
        "binding_sha256":task['binding_sha256'],
        "decision":"APPROVE",
        "finding":"The bounded falsification is scientifically appropriate.",
        "next_action":"Proceed to the bounded build only.",
    })
    applied=ar.validate_result_and_write(sup,task,final,folder)
    assert applied['decision']=='APPROVE'
    assert applied['finding']=='The bounded falsification is scientifically appropriate.'
    assert applied['next_action']=='Proceed to the bounded build only.'
    assert applied['reviewer_model']=='GPT-6 Astra'
    assert applied['reviewer_model_slug']=='gpt-6-astra-fixture'
    assert applied['source_task_id']==task['task_id']
    assert applied['input_sha256']==task['input_sha256']
    assert applied['binding_sha256']==task['binding_sha256']
    assert applied['model_provenance_sha256']
    review,ref=q.load_review(repo,item,'PREBUILD')
    assert ref==q.expected_review_ref(item,'PREBUILD')
    assert review['provenance_kind']==q.PROVENANCE_AUTONOMOUS_RUN
    assert review['reviewer_model']=='GPT-6 Astra'
    assert review['reviewer_model_slug']=='gpt-6-astra-fixture'
    assert review['source_task_id']==task['task_id']


@pytest.mark.parametrize("selection",[
    {"policy":"HIGHEST_AVAILABLE_GPT","visible_astra_count":1,"selected_slug":"gpt-6-astra-fixture"},
    {"policy":"ASTRA_EXACT","visible_astra_count":2,"selected_slug":"gpt-6-astra-fixture"},
])
def test_invalid_worker_selection_cannot_materialize_review(tmp_path,selection):
    repo,sup,path,item=prepare(tmp_path)
    with sup.locked():
        task=ar.select_task(sup,repo,path,item,'PREBUILD')
    folder=sup.root/'runs'/'astra-test'
    folder.mkdir(parents=True)
    (folder/'WORKER.json').write_text(json.dumps({
        "model":"gpt-6-astra-fixture",
        "model_selection":selection,
    }))
    final=json.dumps({
        "candidate_id":"AUTO-CANARY",
        "phase":"PREBUILD",
        "binding_sha256":task['binding_sha256'],
        "decision":"APPROVE",
        "finding":"x",
        "next_action":"y",
    })
    with pytest.raises(ar.AstraAutonomousReviewError):
        ar.validate_result_and_write(sup,task,final,folder)
