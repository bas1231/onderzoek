from pathlib import Path
from datetime import datetime
import importlib.util
import json

ROOT = Path(__file__).resolve().parents[2]

def load_manifest_module():
    path = ROOT / "control/hourly/run_manifest.py"
    spec = importlib.util.spec_from_file_location("run_manifest", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def bootstrap():
    mod = load_manifest_module()
    manifest_path, data = mod.create_manifest()
    report = ROOT / "hourly-reports" / (data["run_id"] + ".md")
    if not report.exists():
        lines = [
            "# Hourly Research Report",
            "",
            "Run: " + data["run_id"],
            "Started: " + data["started_at"],
            "",
            "## Run metadata",
            "Status: STARTED",
            "",
            "## Source coverage",
            "PENDING",
            "",
            "## New evidence",
            "PENDING",
            "",
            "## Candidate hypotheses",
            "UNPROVEN",
            "",
            "## Negative evidence",
            "PENDING",
            "",
            "## Falsification",
            "PENDING",
            "",
            "## Reproduction",
            "PENDING",
            "",
            "## Coverage gaps",
            "PENDING",
            "",
            "## Incidents",
            "NONE YET",
            "",
            "## Decision",
            "NO_PROVEN_EDGE",
            "",
            "## Next hour",
            "PENDING",
        ]
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(chr(10).join(lines) + chr(10))
    return manifest_path, report, data

if __name__ == "__main__":
    m, r, d = bootstrap()
    print(json.dumps({"ok":True,"run_id":d["run_id"],"manifest":str(m.relative_to(ROOT)),"report":str(r.relative_to(ROOT))}, sort_keys=True))
