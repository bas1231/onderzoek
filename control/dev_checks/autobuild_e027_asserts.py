from pathlib import Path

p = Path.home() / 'prediction_research_prod/tests/codex_supervisor/test_autobuild_runtime_wiring_e004i.py'
lines = p.read_text(encoding='utf-8').splitlines()
needle = next(i for i,line in enumerate(lines) if 'GENERIC-NO-PROTOCOL' in line)
start = needle
while start >= 0 and not lines[start].lstrip().startswith('def test_'):
    start -= 1
if start < 0:
    raise SystemExit('WIRING_EXPECTS=FUNCTION_NOT_FOUND')
indent = len(lines[start]) - len(lines[start].lstrip())
end = start + 1
while end < len(lines):
    s = lines[end]
    if s.strip() and (len(s) - len(s.lstrip())) <= indent and s.lstrip().startswith('def test_'):
        break
    end += 1
body = lines[start:end]
selected=[]
for line in body:
    t=line.strip()
    if t.startswith('assert ') or 'candidate_dispatch.apply_candidate_result' in t or "'prospective_protocols'" in t or 'GENERIC-NO-PROTOCOL' in t:
        selected.append(t)
msg=' | '.join(selected)
raise SystemExit('WIRING_EXPECTS='+msg[:5000])
