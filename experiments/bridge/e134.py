from pathlib import Path
p=Path('control/browser_extension/content.js')
t=p.read_text(errors='replace')
for k in ['outbox','/ack']:
 i=t.find(k)
 print('
KEY',k,'AT',i)
 print(t[max(0,i-1800):i+2600])