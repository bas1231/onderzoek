"""Canonical wake-loop gedrag; geen browser/netwerk, geen live verzending."""
import json
from pathlib import Path
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[2]
JS = r'''
const fs=require('fs'), config=JSON.parse(process.argv[1]);
const cache=new Map(config.cache||[]);
global.GM_getValue=(k,d)=>cache.has(k)?cache.get(k):d;
global.GM_setValue=(k,v)=>cache.set(k,v);
global.GM_registerMenuCommand=()=>{};
let src=fs.readFileSync('control/tampermonkey_multichat/prediction-chat-wake.user.js','utf8');
src=src.slice(0,src.indexOf("  status('script gestart;"));
const harness=`
let now=0,index=0,currentChat='chat-a',sent=[],acks=[],turns=${JSON.stringify(config.turns||[])};
Date.now=()=>now;
sleep=async()=>{};status=()=>{};enabled=()=>true;token=()=>'synthetic';chatIsBusy=()=>false;
ensureTabIdentity=async()=>({stable:true,tabApiOk:true,chatId:currentChat,consumerId:'tab'});
global.document={querySelectorAll:()=>turns.map(t=>({innerText:t,textContent:t}))};
const events=${JSON.stringify(config.events)};
gmRequest=async()=>{
 if(index>=events.length){wakeGeneration++;return {status:204};}
 const e=events[index++];now=e.now||0;currentChat=e.chat||'chat-a';
 return {status:200,responseText:JSON.stringify(e)};
};
submitMessage=async(text)=>{sent.push(text);return ${config.succeeds!==false};};
ack=async(event,chat)=>{acks.push({event,chat,cache:Array.from(cache.entries())});return ${config.ack!==false};};
wakeGeneration=1;
wakeLoop(1).then(()=>console.log(JSON.stringify({sent,acks})));
})();`;
eval(src+harness);
'''

def run(events, **kwargs):
    return json.loads(subprocess.check_output(['node','-e',JS,json.dumps(dict(events=events,**kwargs))],cwd=ROOT,text=True))

def event(i=1,task='T',message='RESULT_READY: T full evidence',**kw):
    return dict(event_id=str(i),task_id=task,message=message,**kw)

def test_task_replayed_with_new_event_is_not_resubmitted():
    out=run([event(1),event(2)])
    assert len(out['sent'])==1 and len(out['acks'])==2

def test_ack_failure_keeps_delivery_memory():
    out=run([event(1),event(2)],ack=False)
    assert len(out['sent'])==1 and len(out['acks'])==2

def test_same_task_changed_result_is_not_silently_dropped():
    out=run([event(1),event(2,message='RESULT_READY: T corrected evidence')])
    assert len(out['sent'])==2

def test_exact_visible_user_turn_recovers_delivery():
    e=event();out=run([e],turns=[e['message']])
    assert out['sent']==[] and len(out['acks'])==1

def test_partial_anchor_is_not_delivery_evidence():
    out=run([event()],turns=['RESULT_READY: T'])
    assert len(out['sent'])==1

def test_retry_backoff_preserves_unacked_event():
    out=run([event(1,now=1),event(1,now=1000),event(1,now=60002)],succeeds=False)
    assert len(out['sent'])==2 and out['acks']==[]

def test_task_memory_written_before_ack():
    out=run([event()])
    assert any('sent_tasks' in k and v for k,v in out['acks'][0]['cache'])


def test_event_memory_survives_new_script_instance():
    first=run([event(task='')])
    storage=[row for row in first['acks'][0]['cache'] if 'sent_events' in row[0]]
    assert storage
    second=run([event(task='')],cache=storage)
    assert second['sent']==[] and len(second['acks'])==1


def test_new_event_receipt_written_before_ack():
    out=run([event()])
    assert any('sent_events' in k and v for k,v in out['acks'][0]['cache'])
