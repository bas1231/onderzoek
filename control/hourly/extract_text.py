from pathlib import Path
from html.parser import HTMLParser
import json
import re

ROOT = Path.cwd()
MANIFESTS = ROOT / "knowledge/documents/manifests"
TEXT = ROOT / "knowledge/documents/text"

class Parser(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]; self.skip=0
    def handle_starttag(self, tag, attrs):
        if tag in {"script","style","noscript"}: self.skip += 1
    def handle_endtag(self, tag):
        if tag in {"script","style","noscript"} and self.skip: self.skip -= 1
    def handle_data(self, data):
        if not self.skip: self.parts.append(data)

def latest_manifest(source_id):
    paths=sorted((MANIFESTS/source_id).glob("*.json"))
    if not paths: raise RuntimeError("no manifest")
    p=paths[-1]; return p,json.loads(p.read_text())

def extract(source_id):
    mp,m=latest_manifest(source_id)
    raw=Path.home()/".local/state/prediction-research/raw"/source_id/(m["sha256"]+".bin")
    body=raw.read_bytes()
    text=body.decode("utf-8",errors="replace")
    c=(m.get("content_type") or "").lower()
    if "html" in c or "<html" in text[:1000].lower():
        parser=Parser(); parser.feed(text); text=" ".join(parser.parts)
    text=re.sub(r"\s+"," ",text).strip()
    outdir=TEXT/source_id; outdir.mkdir(parents=True,exist_ok=True)
    out=outdir/(m["sha256"]+".json")
    data={"source_id":source_id,"document_sha256":m["sha256"],"retrieved_at":m["retrieved_at"],"manifest_ref":str(mp.relative_to(ROOT)),"chars":len(text),"text":text[:250000]}
    if not out.exists(): out.write_text(json.dumps(data,indent=2,sort_keys=True)+chr(10))
    return out,data

if __name__=="__main__":
    print(json.dumps({"ok":True,"ready":True},sort_keys=True))
