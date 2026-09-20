from pathlib import Path
needle='hourly-20260920T020000+0200'
for p in Path('.').rglob('*'):
    if p.is_file() and needle in str(p):
        print('FILE',p)
        try:
            print(p.read_text(errors='replace')[:16000])
        except Exception as e:
            print('READ_ERROR',type(e).name,str(e))