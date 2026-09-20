from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE_DIR = ROOT / "knowledge/candidates"
PHASES = ["DISCOVERED","MECHANISM_DEFINED","PREBUILD_KILLED","DATA_READY","DEVELOPMENT","VALIDATION","HOLDOUT","INDEPENDENT_REPRODUCTION","EXECUTION_REALITY","SHADOW","MICRO_LIVE_ELIGIBLE"]
REQUIRED = {
    "MECHANISM_DEFINED":["mechanism"],
    "PREBUILD_KILLED":["mechanism","prebuild_killer"],
    "DATA_READY":["mechanism","prebuild_killer","data_ready","point_in_time"],
    "DEVELOPMENT":["mechanism","prebuild_killer","data_ready","point_in_time"],
    "VALIDATION":["development","point_in_time"],
    "HOLDOUT":["validation","point_in_time"],
    "INDEPENDENT_REPRODUCTION":["holdout","independent_reproduction"],
    "EXECUTION_REALITY":["signal_edge","market_edge","execution_reality"],
    "SHADOW":["signal_edge","market_edge","execution_reality"],
    "MICRO_LIVE_ELIGIBLE":["signal_edge","market_edge","execution_reality","shadow"],
}
ID_RE = re.compile(r"^[A-Za-z0-9._:-]{3,160}$")

def now():
    return datetime.now(timezone.utc).isoformat()

def path_for(cid):
    if not ID_RE.fullmatch(cid):
        raise ValueError("invalid candidate_id")
    return CANDIDATE_DIR / (cid + ".json")

def load(cid):
    return json.loads(path_for(cid).read_text(encoding="utf-8"))

def save(row):
    row["updated_at"] = now()
    p = path_for(row["candidate_id"])
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(row, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(p)
    return p

def create(cid,lane,hypothesis,mechanism,disconfirmers,point_in_time,signal_metric,market_test,execution_test):
    if path_for(cid).exists():
        raise FileExistsError(cid)
    if not disconfirmers or not point_in_time:
        raise ValueError("candidate must define disconfirmers and point-in-time requirements")
    gates = {k:"PENDING" for k in ["mechanism","prebuild_killer","data_ready","point_in_time","development","validation","holdout","independent_reproduction","signal_edge","market_edge","execution_reality","shadow"]}
    return save({
        "candidate_id":cid,"lane":lane,"hypothesis":hypothesis,"mechanism":mechanism,
        "disconfirming_evidence":disconfirmers,"point_in_time_requirements":point_in_time,
        "signal_metric":signal_metric,"market_edge_test":market_test,"execution_reality_test":execution_test,
        "phase":"DISCOVERED","decision":"UNPROVEN","gates":gates,"evidence":[],"negative_evidence":[],
        "created_at":now(),"updated_at":now(),"live_trading":False,"paid_actions":False,"wallet_actions":False
    })

def gate(cid,name,status,evidence_ref,note=""):
    if status not in {"PASS","FAIL","PARTIAL","NOT_TESTED","PENDING"}:
        raise ValueError("invalid gate status")
    row = load(cid)
    if name not in row["gates"]:
        raise KeyError(name)
    ev = {"at":now(),"gate":name,"status":status,"evidence_ref":evidence_ref,"note":note}
    row["gates"][name] = status
    row["evidence"].append(ev)
    if status == "FAIL":
        row["decision"] = "REJECTED"
        row["negative_evidence"].append(ev)
    return save(row)

def promote(cid,target):
    row = load(cid)
    if row["decision"] == "REJECTED":
        raise ValueError("rejected candidate cannot be promoted")
    if target not in PHASES or PHASES.index(target) != PHASES.index(row["phase"]) + 1:
        raise ValueError("promotion must be exactly one phase")
    for name in REQUIRED.get(target,[]):
        if row["gates"].get(name) != "PASS":
            raise ValueError("required gate not PASS: " + name)
    row["phase"] = target
    row["decision"] = "SURVIVES_STAGE"
    return save(row)
