from pathlib import Path
import subprocess
n=chr(10)
p=Path('control/hourly/change_detection.py')
L=['from pathlib import Path','import json','','ROOT = Path.cwd()','MANIFESTS = ROOT / "knowledge/documents/manifests"','','def source_history(source_id):','    root = MANIFESTS / source_id','    if not root.exists(): return []','    out = []','    for path in sorted(root.glob("*.json")):','        try: out.append((path, json.loads(path.read_text())))','        except Exception: continue','    return out','','def classify(source_id):','    history = source_history(source_id)','    if not history: return {"source_id":source_id,"status":"NO_DATA"}','    current_path, current = history[-1]','    if len(history) == 1: return {"source_id":source_id,"status":"FIRST_SEEN","sha256":current.get("sha256"),"manifest":str(current_path)}','    previous_path, previous = history[-2]','    changed = current.get("sha256") != previous.get("sha256")','    return {"source_id":source_id,"status":"CHANGED" if changed else "UNCHANGED","sha256":current.get("sha256"),"previous_sha256":previous.get("sha256"),"manifest":str(current_path),"previous_manifest":str(previous_path)}','','if __name__ == "__main__":','    print(json.dumps({"ok":True,"manifest_root":str(MANIFESTS)}, sort_keys=True))']
p.parent.mkdir(parents=True,exist_ok=True);p.write_text(n.join(L)+n)
r=lambda a:subprocess.run(a,capture_output=True,text=True,check=False)
c=r(['python3','-m','py_compile',str(p)]);d=r(['git','diff','--check']);ok=c.returncode==0 and d.returncode==0
out='ok='+str(ok)
if ok:
 r(['git','add',str(p)]);cm=r(['git','commit','-m','build(hourly): add source change detection']);ps=r(['git','push','origin','HEAD:main']);out += ' commit='+str(cm.returncode)+' push='+str(ps.returncode)
print(out)