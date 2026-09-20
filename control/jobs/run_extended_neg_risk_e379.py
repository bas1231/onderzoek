from pathlib import Path

root=Path.cwd()
source=root/'control/jobs/neg_risk_manifest_e296.py'
if not source.exists():
    raise SystemExit('known_good_scanner_missing')
text=source.read_text(encoding='utf-8')
old='for off in [0,100,200,300,400]:'
new='for off in [500,600,700,800,900,1000,1100,1200,1300,1400]:'
if text.count(old)!=1:
    raise SystemExit('offset_anchor_unexpected')
text=text.replace(old,new,1)
code=compile(text,str(source),'exec')
exec(code)
