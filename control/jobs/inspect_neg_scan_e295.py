from pathlib import Path

p = Path.cwd() / 'control/jobs/scan_neg_risk_identities_e292.py'
lines = p.read_text(encoding='utf-8').splitlines()
for n in range(64,100):
    if n < len(lines):
        print(n + 1, lines[n])
