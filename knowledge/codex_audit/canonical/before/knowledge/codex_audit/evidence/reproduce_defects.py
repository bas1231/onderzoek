"""Geïsoleerde falsificaties; geen netwerk, productie-mutatie of credentials.

Uitvoering vanuit repository-root: python3 knowledge/codex_audit/evidence/reproduce_defects.py
Alle gerapporteerde waarden zijn synthetische testdata, geen marktobservaties.
"""
import contextlib
import ast
import datetime
from dataclasses import replace
import importlib.util
import io
import json
from pathlib import Path
import runpy
import sys
import subprocess
import tempfile
import os
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def recorder_clock(relative):
    tick = [datetime.datetime(2026, 9, 25, 0, 0, tzinfo=datetime.timezone.utc)]
    receipts = []

    class Clock(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return tick[0]

    class Response:
        status = 200
        headers = {"Content-Type": "application/json"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, *args):
            tick[0] += datetime.timedelta(seconds=5)
            receipts.append(tick[0].isoformat())
            return b'{"timeseries": [], "stations": []}'

    with tempfile.TemporaryDirectory(prefix="audit-clock-") as tmp:
        with patch.object(Path, "home", return_value=Path(tmp)), patch("datetime.datetime", Clock), patch("urllib.request.urlopen", return_value=Response()), contextlib.redirect_stdout(io.StringIO()):
            values = runpy.run_path(str(ROOT / relative))
        manifest = values.get("manifest") or values["summary"]
        stamp = manifest["retrieved_at"]
        return {"source": relative, "reported_retrieved_at": stamp, "actual_mock_body_receipts": receipts, "backdated": any(stamp < x for x in receipts)}


def main():
    results = {"synthetic_only": True, "recorders": [recorder_clock("control/weather/kalshi_weather_index_recorder.py"), recorder_clock("control/weather/twc_hourly_recorder.py")]}
    orch = load("audit_orch", "control/hourly/agent_orchestrator.py")
    result = {"candidate_id": "SYNTHETIC", "status": "PASS", "gates": {k: "PASS" for k in orch.PROOF_GATES}, "economics": {k: None for k in ("fees", "spread", "slippage", "fills", "settlement", "capacity")}}
    gate_results = []
    for edge in (-1, 0, "unknown"):
        result["economics"]["net_edge"] = edge
        allowed, reasons = orch.proof_gate(result, {"SYNTHETIC"})
        gate_results.append({"net_edge": edge, "accepted": allowed, "reasons": reasons})
    results["proof_gate"] = gate_results
    router = load("audit_router", "control/tampermonkey_multichat/command_router.py")
    with tempfile.TemporaryDirectory(prefix="audit-route-") as tmp:
        router.ROUTES = Path(tmp)
        (router.ROUTES / "SYNTHETIC.json").write_text("{")
        rejected = False
        try:
            returned = router.write_route("SYNTHETIC", "chat-test", "consumer-test")
        except ValueError:
            returned, rejected = None, True
        results["corrupt_route"] = {"rejected": rejected, "reported_route": returned, "persisted_route": router.read_route("SYNTHETIC"), "raw_still_corrupt": (router.ROUTES / "SYNTHETIC.json").read_text() == "{"}
    replies = []
    handler = object.__new__(router.Handler)
    handler.path = "/command"
    handler.authorized = lambda: True
    handler.reply = lambda status, data: replies.append(status)
    handler.headers = {"Content-Length": "2"}
    handler.rfile = io.BytesIO(b"[]")
    try:
        handler.do_POST()
        err = None
    except Exception as exc:
        err = type(exc).__name__
    results["nonobject_json"] = {"exception": err, "http_replies": replies}
    # Voer de ongewijzigde process_task-functie uit met alle externe acties gestubd.
    tree = ast.parse((ROOT / "control/executor.py").read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "process_task")
    with tempfile.TemporaryDirectory(prefix="audit-timeout-") as td:
        base = Path(td)
        pending = base / "pending.json"
        pending.write_text("{}")
        task = SimpleNamespace(task_class="infrastructure", task_id="SYNTHETIC", working_directory=".", command=["synthetic"], timeout_seconds=1)
        timeout = subprocess.TimeoutExpired(["synthetic"], 1, output=b"partial stdout", stderr=b"partial stderr")
        import shutil
        ns = {"json": json, "ROOT": base, "RUNNING": base / "running", "RESULTS": base / "results", "Task": SimpleNamespace(model_validate=lambda _: task), "task_provenance_in_head": lambda *a: {"ok": True}, "support_script_in_head": lambda *a: {"ok": True}, "lifecycle_load": lambda *a: {"state": "ACCEPTED"}, "lifecycle_update": lambda *a: None, "WORK_CADENCE": SimpleNamespace(check=lambda **k: {"allowed": True}), "shutil": shutil, "now_iso": lambda: "2026-09-25T00:00:00Z", "current_commit": lambda: "0" * 40, "check_action": lambda _: {"status": "ALLOWED", "reason": "synthetic"}, "subprocess": subprocess}
        ns["RUNNING"].mkdir()
        ns["Path"] = Path
        exec(compile(ast.Module(body=[fn], type_ignores=[]), "control/executor.py", "exec"), ns)
        with patch("subprocess.run", side_effect=timeout):
            try:
                ns["process_task"](pending)
                err = None
            except Exception as exc:
                err = type(exc).__name__ + ": " + str(exc)
        results["executor_timeout"] = {"exception": err, "result_written": (base / "results/SYNTHETIC/RESULT.json").exists(), "running_task_remains": (base / "running/pending.json").exists()}
    mr = load("audit_market_reaction", "control/weather/market_reaction.py")
    from decimal import Decimal
    state = mr.MarketState(ticker="SYNTHETIC", ts_ms=9000, yes_bid=Decimal("0.4"), yes_ask=Decimal("0.6"), no_bid=Decimal("0.4"), no_ask=Decimal("0.6"), yes_bid_qty=Decimal("1"), no_bid_qty=Decimal("1"), transport="ws")
    event = {"available_at_ms": 10000}
    results["coverage_hole"] = mr.analyze_reaction(event, [state], coverage_ms=[9000, 100000])
    state = replace(state, yes_bid=None, yes_ask=None, no_bid=None, no_ask=None)
    results["empty_executable_book"] = mr.analyze_reaction(event, [state], coverage_ms=list(range(9000, 41000, 1000)))
    with tempfile.TemporaryDirectory(prefix="audit-lead-") as td:
        base = Path(td)
        manifests = base / ".local/state/prediction-research/kalshi_weather_index_manifests"
        manifests.mkdir(parents=True)
        protocols = base / "knowledge/candidates/protocols"
        protocols.mkdir(parents=True)
        (protocols / "KWI-FULL-STATION-PRECANONICAL-24H-V1.json").write_text(json.dumps({"prospective_cutoff":"2026-09-20T00:00:00+00:00", "window_end":"2026-09-21T00:00:00+00:00", "minimum_eligible_pairs_per_city":30, "minimum_eligible_cities":2}))
        rows = [
            {"retrieved_at":"2026-09-20T00:00:10+00:00", "cities":[{"city":"nyc", "config_version":"v1", "latest_complete":{"t":100, "v":80, "contributors":1}}]},
            {"retrieved_at":"2026-09-20T00:00:20+00:00", "cities":[{"city":"nyc", "config_version":"v2", "latest_complete":{"t":99, "v":79, "contributors":1}, "latest_incomplete":{"t":100, "stations":[{"temp_f":80}]}}]},
        ]
        for i, row in enumerate(rows):
            (manifests / f"{i}.json").write_text(json.dumps(row))
        try:
            os.chdir(base)
            with patch.object(Path, "home", return_value=base), contextlib.redirect_stdout(io.StringIO()):
                values = runpy.run_path(str(ROOT / "control/jobs/evaluate_kwi_full_station_checkpoint_e369.py"))
        finally:
            os.chdir(ROOT)
        results["negative_lead_cross_config"] = {"eligible_rows": len(values["eligible"]), "leads": [r["lead_seconds_to_first_complete"] for r in values["eligible"]]}
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
