from pathlib import Path
import py_compile
import subprocess

root = Path.cwd()
p = root / 'control/edge_hunter/director.py'
t = p.read_text(encoding='utf-8')
q = chr(34)
nl = chr(10)
needle = '        ' + q + 'wallet_actions' + q + ': False,' + nl
marker = q + 'candidates' + q + ': [load_json(path)'
line = '        ' + q + 'candidates' + q + ': [load_json(path) for path in sorted((ROOT / ' + q + 'knowledge/candidates' + q + ').glob(' + q + '*.json' + q + '))],' + nl
if marker not in t:
    if needle not in t:
        raise SystemExit('insertion_point_missing')
    t = t.replace(needle, needle + line, 1)
    p.write_text(t, encoding='utf-8')
py_compile.compile(str(p), doraise=True)
subprocess.run(['git','add','control/edge_hunter/director.py'], cwd=root, check=True)
subprocess.run(['git','commit','--only','control/edge_hunter/director.py','-m','add candidates to edge packet'], cwd=root, check=True)
subprocess.run(['git','push'], cwd=root, check=True)
print('EDGE_PACKET_CANDIDATES_PATCH_PASS')
