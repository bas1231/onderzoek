from pathlib import Path
import json,subprocess
p=Path('control/hourly/source_registry.py')
n=chr(10)
q=chr(34)
L=[]
L.append('from pathlib import Path')
L.append('import json')
L.append('')
L.append('ROOT = Path.cwd()')
L.append('REGISTRY = ROOT / '+q+'knowledge/sources/registry.json'+q)
L.append('')
L.append('def load_registry():')
L.append('    data = json.loads(REGISTRY.read_text())')
L.append('    seen = set()')
L.append('    for source in data.get('+q+'sources'+q+', []):')
L.append('        sid = source.get('+q+'id'+q+')')
L.append('        if not sid: raise RuntimeError('+q+'missing source id'+q+')')
L.append('        if sid in seen: raise RuntimeError('+q+'duplicate source id: '+q+' + sid)')
L.append('        seen.add(sid)')
L.append('        if source.get('+q+'cost_class'+q+') != '+q+'free_public'+q+': raise RuntimeError('+q+'non-free source blocked: '+q+' + sid)')
L.append('    return data')
L.append('')
L.append('if __name__ == '+q+'__main__'+q+':')
L.append('    data = load_registry()')
L.append('    print(json.dumps({'+q+'ok'+q+': True, '+q+'sources'+q+': len(data['+q+'sources'+q+'])}, sort_keys=True))')
p.parent.mkdir(parents=True,exist_ok=True)
p.write_text(n.join(L)+n)
r=lambda a:subprocess.run(a,capture_output=True,text=True,check=False)
v=r(['.venv/bin/python',str(p)])
d=r(['git','diff','--check'])
ok=v.returncode==0 and d.returncode==0
out={'ok':ok,'validator':v.stdout.strip(),'stderr':v.stderr.strip()}
if ok:
 r(['git','add',str(p)])
 c=r(['git','commit','-m','build(research): enforce free source registry'])
 z=r(['git','push','origin','HEAD:main'])
 out['commit_rc']=c.returncode
 out['push_rc']=z.returncode
print(json.dumps(out))