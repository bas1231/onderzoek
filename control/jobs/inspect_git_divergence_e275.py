from pathlib import Path
import subprocess

root = Path.cwd()

def run(args):
    r = subprocess.run(args, cwd=root, capture_output=True, text=True)
    print('CMD', ' '.join(args))
    print('RC', r.returncode)
    if r.stdout:
        print(r.stdout)
    if r.stderr:
        print(r.stderr)
    return r

run(['git','status','--short'])
run(['git','log','--oneline','--decorate','-n','12'])
run(['git','fetch','origin'])
run(['git','rev-list','--left-right','--count','HEAD...origin/main'])
run(['git','log','--oneline','HEAD..origin/main'])
run(['git','log','--oneline','origin/main..HEAD'])
