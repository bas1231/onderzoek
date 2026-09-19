from pathlib import Path
import subprocess,json
nl=chr(10)
files={'knowledge/README.md':['# Knowledge Base','','Immutable-first research store for sources, claims, mechanisms, runs, candidates and negative evidence.'], 'knowledge/SCHEMA.md':['# Research schema','','Core entities: source, document, claim, mechanism, candidate, run, incident.','','Every claim must preserve provenance, retrieval time, source type, confidence and falsification status.'], 'control/hourly/README.md':['# Hourly Research','','Hourly autonomous research remains research-only. No live trading, paid APIs, wallet actions or spend without explicit approval.']}
for name,lines in files.items():
 p=Path(name);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(nl.join(lines)+nl)
for d in ['knowledge/sources','knowledge/documents','knowledge/claims','knowledge/mechanisms','knowledge/candidates','knowledge/runs','knowledge/source_changes','negative_evidence','agents']:
 Path(d).mkdir(parents=True,exist_ok=True)
run=lambda a:subprocess.run(a,capture_output=True,text=True,check=False)
run(['git','add','knowledge','control/hourly/README.md']);c=run(['git','commit','-m','build(research): create knowledge schema']);p=run(['git','push','origin','HEAD:main']);print(json.dumps({'commit_rc':c.returncode,'push_rc':p.returncode,'head':run(['git','log','-1','--oneline']).stdout.strip()},indent=2))