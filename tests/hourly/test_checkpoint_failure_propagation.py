import json,runpy,subprocess
from pathlib import Path
from types import SimpleNamespace
import pytest
ROOT=Path(__file__).resolve().parents[2]
@pytest.mark.parametrize('name,protocol',[('hourly_asset_fill_checkpoint_e354.py','ASSET-RANK-MAKER-HEDGE-V1-fill-feasibility-24h-v1.json'),('hourly_kwi_full_station_checkpoint_e371.py','KWI-FULL-STATION-PRECANONICAL-24H-V1.json')])
@pytest.mark.parametrize('failure',[7,'timeout'])
def test_inner_failure_is_never_outer_success(tmp_path,monkeypatch,name,protocol,failure):
    p=tmp_path/'knowledge/candidates/protocols'/protocol;p.parent.mkdir(parents=True);p.write_text(json.dumps({'window_end':'2099-01-01T00:00:00+00:00'}))
    e=tmp_path/'control/jobs/evaluate_kwi_full_station_checkpoint_e369.py';e.parent.mkdir(parents=True);e.write_text('')
    monkeypatch.chdir(tmp_path);monkeypatch.setattr(Path,'home',classmethod(lambda cls:tmp_path))
    def fail(*a,**kw):
        if failure=='timeout':raise subprocess.TimeoutExpired('synthetic',1)
        return SimpleNamespace(returncode=failure)
    monkeypatch.setattr(subprocess,'run',fail)
    with pytest.raises(SystemExit) as exc:runpy.run_path(str(ROOT/'control/jobs'/name),run_name='__main__')
    assert exc.value.code!=0
    assert not list(tmp_path.rglob('*finalized.json'))
