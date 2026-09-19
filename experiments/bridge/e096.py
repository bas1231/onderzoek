from pathlib import Path
import subprocess
p=Path('AGENTS.md')
t=p.read_text() if p.exists() else '# Agent Rules'+chr(10)
rule='## Stop-check autonomy rule'+chr(10)+chr(10)+'Before stopping, pausing, or waiting, explicitly check whether stopping is actually necessary. If useful work can safely continue within existing authorization, at zero additional cost, and without live trading or wallet actions, continue autonomously instead of stopping. Stop only for a real blocker, required approval, missing essential input, safety boundary, paid action, live trading, or wallet action.'+chr(10)
if '## Stop-check autonomy rule' not in t:
 if not t.endswith(chr(10)): t += chr(10)
 t += chr(10)+rule
 p.write_text(t)
r=lambda a:subprocess.run(a,capture_output=True,text=True,check=False)
d=r(['git','diff','--check']);ok=d.returncode==0
out='ok='+str(ok)
if ok:
 r(['git','add','AGENTS.md']);c=r(['git','commit','-m','control: require stop necessity check']);z=r(['git','push','origin','HEAD:main']);out += ' commit='+str(c.returncode)+' push='+str(z.returncode)
print(out)