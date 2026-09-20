from pathlib import Path
import json

ROOT = Path.cwd()
RUNS = ROOT / "knowledge/runs"

AGENT_STATES = {
    "PENDING",
    "READY",
    "RUNNING",
    "NO_EVIDENCE",
    "WAITING_FOR_DATA",
    "WAITING_FOR_RESULT",
    "RESULT_READY",
    "COMPLETED",
    "FAILED",
    "FALSIFIED",
    "PARKED",
}
SOURCE_STATES = {"PENDING","FETCHED","UNCHANGED","CHANGED","FAILED","SKIPPED"}
GATE_STATES = {"PENDING","PASS","FAIL","NOT_TESTED"}

def latest_run_path():
    paths = sorted(RUNS.glob("hourly-*.json"))
    if not paths: raise RuntimeError("no hourly run manifest")
    return paths[-1]

def load(path=None):
    path = path or latest_run_path()
    return path, json.loads(path.read_text())

def save(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + chr(10))

def set_agent(agent_id, state, output_refs=None):
    if state not in AGENT_STATES: raise ValueError("invalid agent state")
    path, data = load()
    if agent_id not in data["agents"]: raise KeyError(agent_id)
    data["agents"][agent_id] = state
    data.setdefault("agent_outputs", {})[agent_id] = output_refs or []
    save(path, data)
    return path

def set_source(source_id, state, manifest_ref=None):
    if state not in SOURCE_STATES: raise ValueError("invalid source state")
    path, data = load()
    if source_id not in data["sources"]: raise KeyError(source_id)
    data["sources"][source_id] = state
    if manifest_ref: data.setdefault("source_manifests", {})[source_id] = manifest_ref
    save(path, data)
    return path

def set_gate(gate, state):
    if state not in GATE_STATES: raise ValueError("invalid gate state")
    path, data = load()
    if gate not in data["gates"]: raise KeyError(gate)
    data["gates"][gate] = state
    save(path, data)
    return path

if __name__ == "__main__":
    path, data = load()
    print(json.dumps({"ok":True,"run_id":data["run_id"],"agents":len(data["agents"]),"sources":len(data["sources"])}, sort_keys=True))
