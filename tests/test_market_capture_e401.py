import json
from pathlib import Path

from control.weather.market_capture_e401 import WsEvidenceRecorder, capture_rest_snapshot


def read_rows(path: Path):
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def test_rest_capture_writes_state(tmp_path):
    p=tmp_path/"states.jsonl"
    row=capture_rest_snapshot("KXTEMP-X",{"orderbook_fp":{"yes_dollars":[["0.50","2"]],"no_dollars":[["0.49","3"]]}},p,received_at_ms=10000)
    assert row["yes_bid"]=="0.50"
    assert row["yes_ask"]=="0.51"
    assert read_rows(p)[0]["capture_kind"]=="rest_snapshot"


def test_ws_snapshot_delta_and_coverage(tmp_path):
    state=tmp_path/"states.jsonl"; gaps=tmp_path/"gaps.jsonl"; cov=tmp_path/"coverage.jsonl"
    rec=WsEvidenceRecorder("KXTEMP-X",state,gaps,cov)
    rec.ingest({"type":"orderbook_snapshot","seq":1,"msg":{"market_ticker":"KXTEMP-X","yes_dollars_fp":[["0.50","10"]],"no_dollars_fp":[["0.49","10"]]}},received_at_ms=10000)
    rec.ingest({"type":"orderbook_delta","seq":2,"msg":{"market_ticker":"KXTEMP-X","side":"yes","price_dollars":"0.50","delta_fp":"-2"}},received_at_ms=11000)
    rows=read_rows(state)
    assert len(rows)==2
    assert rows[-1]["yes_bid_qty"]=="8"
    assert len(read_rows(cov))==2
    assert read_rows(gaps)==[]


def test_ws_gap_is_recorded_and_raised(tmp_path):
    state=tmp_path/"states.jsonl"; gaps=tmp_path/"gaps.jsonl"; cov=tmp_path/"coverage.jsonl"
    rec=WsEvidenceRecorder("KXTEMP-X",state,gaps,cov)
    rec.ingest({"type":"orderbook_snapshot","seq":1,"msg":{"market_ticker":"KXTEMP-X","yes_dollars_fp":[["0.50","10"]],"no_dollars_fp":[["0.49","10"]]}},received_at_ms=10000)
    try:
        rec.ingest({"type":"orderbook_delta","seq":3,"msg":{"market_ticker":"KXTEMP-X","side":"yes","price_dollars":"0.50","delta_fp":"-1"}},received_at_ms=11000)
    except ValueError:
        pass
    else:
        raise AssertionError("sequence gap must raise")
    gap_rows=read_rows(gaps)
    assert len(gap_rows)==1
    assert "sequence gap" in gap_rows[0]["reason"]
    assert rec.book.ready is False
