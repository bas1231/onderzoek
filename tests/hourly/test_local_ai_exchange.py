"""Bounded transport contracts; these unit tests do not claim model E2E."""
import importlib.util
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace
import pytest

ROOT = Path.cwd()
PROPOSAL = ROOT if (ROOT / 'control/hourly/local_ai_exchange.py').exists() else Path(__file__).resolve().parents[2]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def setup(tmp_path):
    target = tmp_path / 'control/hourly'
    target.mkdir(parents=True)
    for name in ('ai_work_exchange.py', 'ai_response_receiver.py'):
        shutil.copy2(ROOT / 'control/hourly' / name, target / name)
    shutil.copy2(PROPOSAL / 'control/hourly/local_ai_exchange.py', target / 'local_ai_exchange.py')
    mod = load(target / 'local_ai_exchange.py', 'local_transport_test')
    contract = load(target / 'ai_work_exchange.py', 'local_contract_test')
    fixture = load(ROOT / 'tests/hourly/test_ai_work_exchange_v14.py', 'local_fixture_test')
    request = contract.build_request(fixture.bundle(['settlement']), source_commit='a'*40)
    contract.write_request(request)
    return mod, request


def test_pending_is_not_delivered(tmp_path):
    mod, request = setup(tmp_path)
    value = mod.publish_request(request)
    assert value['status'] == 'DISPATCH_PENDING'
    assert not value['published'] and not value['model_roundtrip_proven']


@pytest.mark.parametrize('flag', ['live_trading', 'wallet_actions', 'paid_actions', 'openai_api'])
def test_unsafe_request_rejected(tmp_path, flag):
    mod, request = setup(tmp_path)
    request['governor'][flag] = True
    with pytest.raises(ValueError):
        mod.publish_request(request)


def test_provenance_mismatch(tmp_path):
    mod, request = setup(tmp_path)
    path = tmp_path / 'knowledge/ai_exchange/requests' / (request['run_id'] + '.json')
    value = json.loads(path.read_text())
    value['source_commit'] = 'b'*40
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        mod.publish_request(request)


def test_malformed_response_visible(tmp_path):
    mod, request = setup(tmp_path)
    folder = tmp_path / 'knowledge/ai_exchange/responses'
    folder.mkdir(parents=True)
    (folder / (request['run_id'] + '.json')).write_text('[]')
    result = mod.ingest_local_responses()
    assert result['ok'] is False and result['errors']


def test_unknown_mode_fails_before_import(monkeypatch):
    wake = load(PROPOSAL / 'control/hourly/hourly_wake.py', 'local_wake_invalid')
    monkeypatch.setenv('PREDICTION_EXECUTION_MODE', 'typo')
    monkeypatch.setattr(wake, 'load_module', lambda *args: pytest.fail('unexpected import'))
    with pytest.raises(ValueError):
        wake.main()


def test_local_mode_never_imports_git(tmp_path, monkeypatch):
    wake = load(PROPOSAL / 'control/hourly/hourly_wake.py', 'local_wake_selection')
    monkeypatch.setenv('PREDICTION_EXECUTION_MODE', 'qualification_local')
    monkeypatch.setattr(wake, 'ROOT', tmp_path)
    seen = []
    def loader(name, path):
        seen.append(path.name)
        assert path.name != 'git_ai_exchange.py'
        if path.name == 'local_ai_exchange.py':
            return SimpleNamespace(ingest_local_responses=lambda: {'ok': True})
        return SimpleNamespace()
    monkeypatch.setattr(wake, 'load_module', loader)
    monkeypatch.setattr(wake, 'browser_fallback', lambda *args: {'used': True})
    assert wake.main() == 1  # Missing current bundle must not report success.
    assert seen == ['ai_work_exchange.py', 'local_ai_exchange.py']
