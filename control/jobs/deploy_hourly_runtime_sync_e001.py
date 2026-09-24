from pathlib import Path
import shutil, subprocess, json

ROOT = Path(__file__).resolve().parents[2]
service_src = ROOT / "control/hourly/systemd/prediction-research-hourly-director.service"
timer_src = ROOT / "control/hourly/systemd/prediction-research-hourly-director.timer"
dst_dir = Path.home() / ".config/systemd/user"
service_dst = dst_dir / service_src.name
timer_dst = dst_dir / timer_src.name
dst_dir.mkdir(parents=True, exist_ok=True)

service_text = service_src.read_text(encoding="utf-8")
timer_text = timer_src.read_text(encoding="utf-8")
required_service_lines = (
    "WorkingDirectory=%h/prediction_research_prod",
    "ExecStartPre=%h/prediction_research_prod/.venv/bin/python %h/prediction_research_prod/control/hourly/runtime_sync.py",
    "ExecStart=%h/prediction_research_prod/.venv/bin/python %h/prediction_research_prod/control/hourly/edge_hunter_cycle.py",
    "ExecStartPost=%h/prediction_research_prod/.venv/bin/python %h/prediction_research_prod/control/hourly/runtime_health.py",
)
missing = [line for line in required_service_lines if line not in service_text]
if missing:
    raise SystemExit("FAIL: canonical unit lacks prod runtime contract: " + "; ".join(missing))
if "%h/prediction_research/" in service_text or "WorkingDirectory=/home/leonh/prediction_research" in service_text:
    raise SystemExit("FAIL: canonical unit still references legacy non-prod runtime path")
if "OnCalendar=*-*-* *:00:00" not in timer_text or "Persistent=true" not in timer_text:
    raise SystemExit("FAIL: canonical timer lacks hourly persistent contract")

# Install BOTH canonical units.  The previous deployer copied only the service
# and then enabled whatever timer happened to be installed already.  That
# allowed a missing/stale timer to survive indefinitely.
for src_text, dst in ((service_text, service_dst), (timer_text, timer_dst)):
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    tmp.write_text(src_text, encoding="utf-8")
    tmp.replace(dst)

def run(*args):
    p=subprocess.run(args,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False,timeout=60)
    if p.returncode:
        raise SystemExit("FAIL "+ " ".join(args)+": "+(p.stderr or p.stdout)[-1000:])
    return p.stdout.strip()

run("systemctl","--user","daemon-reload")
run("systemctl","--user","enable","--now","prediction-research-hourly-director.timer")
service_cat=run("systemctl","--user","cat","prediction-research-hourly-director.service")
timer_cat=run("systemctl","--user","cat","prediction-research-hourly-director.timer")
missing_installed = [line for line in required_service_lines if line not in service_cat]
if missing_installed:
    raise SystemExit("FAIL: installed unit lacks prod runtime contract: " + "; ".join(missing_installed))
if "%h/prediction_research/" in service_cat or "WorkingDirectory=/home/leonh/prediction_research" in service_cat:
    raise SystemExit("FAIL: installed unit still references legacy non-prod runtime path")
if "OnCalendar=*-*-* *:00:00" not in timer_cat or "Persistent=true" not in timer_cat:
    raise SystemExit("FAIL: installed timer is stale or malformed")
enabled=run("systemctl","--user","is-enabled","prediction-research-hourly-director.timer")
active=run("systemctl","--user","is-active","prediction-research-hourly-director.timer")
if enabled != "enabled" or active != "active":
    raise SystemExit(f"FAIL: timer not live after install: enabled={enabled!r} active={active!r}")
print(json.dumps({"status":"PASS","runtime_sync_preflight_installed":True,"prod_runtime_path_installed":True,"canonical_timer_installed":True,"timer_enabled":enabled,"timer_active":active,"live_trading":False,"paid_actions":False,"wallet_actions":False},sort_keys=True))
