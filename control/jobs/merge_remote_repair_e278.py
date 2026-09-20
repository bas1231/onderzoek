import subprocess

allowed = {'control/browser_extension/repair_bridge.py'}

def run(args, check=True):
    r = subprocess.run(args, capture_output=True, text=True)
    print('CMD', ' '.join(args))
    if r.stdout.strip():
        print(r.stdout.strip())
    if r.stderr.strip():
        print(r.stderr.strip())
    if check and r.returncode:
        raise SystemExit(r.returncode)
    return r

run(['git','fetch','origin'])
files = run(['git','diff','--name-only','HEAD...origin/main']).stdout.splitlines()
remote = run(['git','log','--oneline','HEAD..origin/main']).stdout.splitlines()
print('REMOTE_ONLY_COMMITS', len(remote))
print('REMOTE_CHANGED_FILES', ','.join(files))
if set(files) - allowed:
    raise SystemExit('unexpected_remote_files')
if remote:
    run(['git','merge','--no-edit','origin/main'])
run(['git','push','origin','main'])
count = run(['git','rev-list','--left-right','--count','HEAD...origin/main']).stdout.strip()
if count != '0	0':
    raise SystemExit('remote_not_synchronized')
print('GIT_SYNC_PASS')
