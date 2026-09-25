"""Safety regression: uitsluitend tijdelijke bestanden, systemctl gemockt."""
import json
from pathlib import Path
import pytest
import reconcile_wsl as m

@pytest.fixture
def fixture(tmp_path,monkeypatch):
    home=tmp_path/'home';root=home/'prediction_research_prod';here=root/'knowledge/codex_audit/runtime_reconcile';here.mkdir(parents=True)
    monkeypatch.setattr(m,'ROOT',root);monkeypatch.setattr(m,'HERE',here);monkeypatch.setattr(Path,'home',classmethod(lambda cls:home))
    for index in [root/'.git/index',home/'prediction_research/.git/index']:
        index.parent.mkdir(parents=True);index.write_bytes(b'owner-index')
    owner=root/'owner.txt';owner.write_text('owner')
    paths=['control/tampermonkey_multichat/command_router.py','control/weather/kalshi_weather_index_recorder.py','control/weather/twc_hourly_recorder.py','control/weather/market_reaction.py','control/jobs/evaluate_kwi_full_station_checkpoint_e369.py']
    rows=[]
    for i,p in enumerate(paths):
        target=home/('.local/share/prediction-chat-bridge/command_router.py' if i==0 else 'prediction_research/'+p)
        for f,data in [(target,b'before'),(root/p,b'after'),(here/'payload'/p,b'after')]:f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
        rows.append({'source':p,'target':str(target),'before_sha256':m.sha(target),'after_sha256':m.sha(root/p)})
    unit=home/'.config/systemd/user/prediction-chat-router.service';unit.parent.mkdir(parents=True);unit.write_bytes(b'unit')
    (here/'unit_manifest.json').write_text(json.dumps({'router_unit_sha256':m.sha(unit)}))
    (here/'preservation_manifest.json').write_text(json.dumps({'paths':rows,'owner_work':{'owner.txt':m.sha(owner)},'index_sha256':m.sha(root/'.git/index')}))
    commands=[]
    monkeypatch.setattr(m,'command',lambda args:commands.append(args) or '')
    monkeypatch.setattr(m,'run',lambda *a,**kw:0)
    return rows,commands

def test_deploy_and_idempotent_repeat_preserve_owner(fixture):
    rows,commands=fixture
    assert m.main()==0 and m.main()==0
    assert all(Path(x['target']).read_bytes()==b'after' for x in rows)
    assert (m.ROOT/'owner.txt').read_text()=='owner'
    assert (m.ROOT/'.git/index').read_bytes()==b'owner-index'
    assert all(c[0]=='systemctl' for c in commands)
    assert all('prediction-research-hourly-director.service' not in c for c in commands if 'try-restart' in c)

def test_owner_conflict_refuses_all_writes(fixture):
    rows,_=fixture;Path(rows[-1]['target']).write_bytes(b'new owner work')
    assert m.main()==1
    assert all(Path(x['target']).read_bytes()==b'before' for x in rows[:-1])
    assert Path(rows[-1]['target']).read_bytes()==b'new owner work'

def test_failed_tests_refuse_deployment(fixture,monkeypatch):
    rows,_=fixture;monkeypatch.setattr(m,'run',lambda *a,**kw:1)
    assert m.main()==1
    assert all(Path(x['target']).read_bytes()==b'before' for x in rows)

def test_index_change_refuses_deployment(fixture):
    rows,_=fixture;(m.ROOT/'.git/index').write_bytes(b'new staged work')
    assert m.main()==1
    assert all(Path(x['target']).read_bytes()==b'before' for x in rows)
