from pathlib import Path
import subprocess
n=chr(10)
p=Path('control/hourly/collector.py')
L=['from pathlib import Path','from datetime import datetime, timezone','import hashlib','import json','import urllib.request','','ROOT = Path.cwd()','REGISTRY = ROOT / "knowledge/sources/registry.json"','RAW = Path.home() / ".local/state/prediction-research/raw"','MANIFESTS = ROOT / "knowledge/documents/manifests"','','def load_sources():','    data = json.loads(REGISTRY.read_text())','    sources = data.get("sources", [])','    for source in sources:','        if source.get("cost_class") != "free_public":','            raise RuntimeError("non-free source blocked")','    return sources','','def fetch(source):','    request = urllib.request.Request(source["url"], headers={"User-Agent":"PredictionResearch-public"})','    with urllib.request.urlopen(request, timeout=15) as response:','        body = response.read(750000)','        headers = dict(response.headers)','        status = int(getattr(response, "status", 200))','    return body, headers, status','','def archive(source, body, headers, status):','    now = datetime.now(timezone.utc)','    digest = hashlib.sha256(body).hexdigest()','    rawdir = RAW / source["id"]','    rawdir.mkdir(parents=True, exist_ok=True)','    rawpath = rawdir / (digest + ".bin")','    is_new = not rawpath.exists()','    if is_new:','        rawpath.write_bytes(body)','    mdir = MANIFESTS / source["id"]','    mdir.mkdir(parents=True, exist_ok=True)','    data = {"source_id":source["id"],"retrieved_at":now.isoformat(),"sha256":digest,"bytes":len(body),"http_status":status,"content_type":headers.get("Content-Type"),"etag":headers.get("ETag"),"last_modified":headers.get("Last-Modified"),"is_new_content":is_new,"cost_class":"free_public"}','    mp = mdir / (now.strftime("%Y%m%dT%H%M%SZ") + "_" + digest[:12] + ".json")','    mp.write_text(json.dumps(data, indent=2, sort_keys=True) + chr(10))','    return data','','if __name__ == "__main__":','    sources = load_sources()','    print(json.dumps({"ok":True,"sources":len(sources)}, sort_keys=True))']
p.parent.mkdir(parents=True,exist_ok=True)
p.write_text(n.join(L)+n)
r=lambda a:subprocess.run(a,capture_output=True,text=True,check=False)
c=r(['python3','-m','py_compile',str(p)])
v=r(['.venv/bin/python',str(p)])
d=r(['git','diff','--check'])
ok=c.returncode==0 and v.returncode==0 and d.returncode==0
out='ok='+str(ok)+' validator='+v.stdout.strip()
if ok:
 r(['git','add',str(p)])
 cm=r(['git','commit','-m','build(hourly): add public source collector'])
 ps=r(['git','push','origin','HEAD:main'])
 out += ' commit='+str(cm.returncode)+' push='+str(ps.returncode)
print(out)