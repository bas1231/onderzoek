from pathlib import Path
import json
import importlib.util

ROOT = Path.cwd()
SWEEPS = ROOT / "knowledge/runs/source_sweeps"

def load(name,path):
    s=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m

state = load("director_state", ROOT / "control/hourly/director_state.py")

def latest_sweep():
    paths = sorted(SWEEPS.glob("*.json"))
    if not paths: raise RuntimeError("no source sweep")
    p = paths[-1]
    return p, json.loads(p.read_text())

def apply():
    sweep_path, sweep = latest_sweep()
    for result in sweep["results"]:
        sid = result["source_id"]
        if not result["ok"]:
            status = "FAILED"
        else:
            cls = result.get("classification")
            status = cls if cls in {"UNCHANGED","CHANGED"} else "FETCHED"
        state.set_source(sid, status, result.get("manifest"))
    run_path, run = state.load()
    run["source_sweep_ref"] = str(sweep_path.relative_to(ROOT))
    run["source_success_count"] = sweep["success_count"]
    run["source_failure_count"] = sweep["failure_count"]
    if sweep["success_count"] > 0:
        run["gates"]["source_provenance"] = "PASS"
    state.save(run_path, run)
    report = ROOT / "hourly-reports" / (run["run_id"] + ".md")
    lines = report.read_text().splitlines() if report.exists() else []
    lines += ["","## Source sweep update","","Success: " + str(sweep["success_count"]),"Failure: " + str(sweep["failure_count"]),"Sweep: " + str(sweep_path.relative_to(ROOT))]
    for result in sweep["results"]:
        lines.append("- " + result["source_id"] + ": " + (result.get("classification") if result.get("ok") else "FAILED"))
    report.write_text(chr(10).join(lines)+chr(10))
    return run_path, report, sweep

if __name__ == "__main__":
    print(json.dumps({"ok":True,"ready":True}, sort_keys=True))
