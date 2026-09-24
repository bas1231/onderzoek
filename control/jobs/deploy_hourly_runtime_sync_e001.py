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
required = "ExecStartPre=%h/prediction_research/.venv/bin/python %h/prediction_research/control/hourly/runtime_sync.py"
if required not in service_text:
    raise SystemExit("FAIL: canonical unit lacks runtime sync preflight")
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
if required not in service_cat:
    raise SystemExit("FAIL: installed unit does not contain runtime sync preflight")
if "OnCalendar=*-*-* *:00:00" not in timer_cat or "Persistent=true" not in timer_cat:
    raise SystemExit("FAIL: installed timer is stale or malformed")
enabled=run("systemctl","--user","is-enabled","prediction-research-hourly-director.timer")
active=run("systemctl","--user","is-active","prediction-research-hourly-director.timer")
if enabled != "enabled" or active != "active":
    raise SystemExit(f"FAIL: timer not live after install: enabled={enabled!r} active={active!r}")
print(json.dumps({"status":"PASS","runtime_sync_preflight_installed":True,"canonical_timer_installed":True,"timer_enabled":enabled,"timer_active":active,"live_trading":False,"paid_actions":False,"wallet_actions":False},sort_keys=True))
