import subprocess

def out(args):
    r = subprocess.run(args, capture_output=True, text=True)
    print('CMD', ' '.join(args))
    print(r.stdout.strip())
    if r.stderr.strip():
        print('ERR', r.stderr.strip())
    if r.returncode:
        raise SystemExit(r.returncode)

out(['git','fetch','origin'])
out(['git','rev-list','--left-right','--count','HEAD...origin/main'])
out(['git','merge-base','HEAD','origin/main'])
out(['git','log','--oneline','-n','15','origin/main..HEAD'])
out(['git','log','--oneline','-n','15','HEAD..origin/main'])
