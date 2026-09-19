from pathlib import Path
import subprocess
n=chr(10)
p=Path('control/hourly/claim_store.py')
L=['from pathlib import Path','from datetime import datetime, timezone','import hashlib','import json','','ROOT = Path.cwd()','CLAIMS = ROOT / "knowledge/claims"','','def claim_id(source_id, document_sha256, statement):','    raw = (source_id + "|" + document_sha256 + "|" + statement).encode()','    return hashlib.sha256(raw).hexdigest()','','def store_claim(source_id, document_sha256, statement, evidence_grade, status="UNPROVEN", retrieved_at=None, metadata=None):','    if status not in {"UNPROVEN","SUPPORTED","FALSIFIED","REPRODUCED"}:','        raise ValueError("invalid claim status")','    if evidence_grade not in {"primary","secondary","discovery"}:','        raise ValueError("invalid evidence grade")','    cid = claim_id(source_id, document_sha256, statement)','    data = {','        "claim_id": cid,','        "source_id": source_id,','        "document_sha256": document_sha256,','        "statement": statement,','        "evidence_grade": evidence_grade,','        "status": status,','        "retrieved_at": retrieved_at or datetime.now(timezone.utc).isoformat(),','        "metadata": metadata or {}','    }','    CLAIMS.mkdir(parents=True, exist_ok=True)','    path = CLAIMS / (cid + ".json")','    if not path.exists():','        path.write_text(json.dumps(data, indent=2, sort_keys=True) + chr(10))','    return path, data','','if __name__ == "__main__":','    test = claim_id("source","0"*64,"example")','    print(json.dumps({"ok":True,"claim_id_length":len(test)}, sort_keys=True))']
p.parent.mkdir(parents=True,exist_ok=True);p.write_text(n.join(L)+n)
r=lambda a:subprocess.run(a,capture_output=True,text=True,check=False)
c=r(['python3','-m','py_compile',str(p)]);v=r(['.venv/bin/python',str(p)]);d=r(['git','diff','--check']);ok=c.returncode==0 and v.returncode==0 and d.returncode==0
out='ok='+str(ok)+' validator='+v.stdout.strip()
if ok:
 r(['git','add',str(p)]);cm=r(['git','commit','-m','build(research): add provenance claim store']);ps=r(['git','push','origin','HEAD:main']);out += ' commit='+str(cm.returncode)+' push='+str(ps.returncode)
print(out)