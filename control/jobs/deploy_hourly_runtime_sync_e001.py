from pathlib import Path
import shutil, subprocess, json

ROOT = Path(__file__).resolve().parents[2]
src = ROOT / "control/hourly/systemd/prediction-research-hourly-director.service"
dst_dir = Path.home() / ".config/systemd/user"
dst = dst_dir / src.name
dst_dir.mkdir(parents=True, exist_ok=True)

text = src.read_text(encoding="utf-8")
required = "ExecStartPre=%h/prediction_research/.venv/bin/python %h/prediction_research/control/hourly/runtime_sync.py"
if required not in text:
    raise SystemExit("FAIL: canonical unit lacks runtime sync preflight")

tmp = dst.with_suffix(".service.tmp")
tmp.write_text(text, encoding="utf-8")
tmp.replace(dst)

def run(*args):
    p=subprocess.run(args,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False,timeout=60)
    if p.returncode:
        raise SystemExit("FAIL "+ " ".join(args)+": "+(p.stderr or p.stdout)[-1000:])
    return p.stdout.strip()

run("systemctl","--user","daemon-reload")
run("systemctl","--user","enable","prediction-research-hourly-director.timer")
cat=run("systemctl","--user","cat","prediction-research-hourly-director.service")
if required not in cat:
    raise SystemExit("FAIL: installed unit does not contain runtime sync preflight")
active=run("systemctl","--user","is-enabled","prediction-research-hourly-director.timer")
print(json.dumps({"status":"PASS","runtime_sync_preflight_installed":True,"timer_enabled":active,"live_trading":False,"paid_actions":False,"wallet_actions":False},sort_keys=True))
