import subprocess

def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    print('CMD', ' '.join(args))
    print(r.stdout.strip())
    if r.stderr.strip():
        print('ERR', r.stderr.strip())
    if r.returncode:
        raise SystemExit(r.returncode)

run(['git','show','--stat','--oneline','origin/main'])
run(['git','show','--name-status','--format=fuller','origin/main'])
run(['git','diff','--name-only','375073c..origin/main'])
