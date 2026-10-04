from __future__ import annotations
import subprocess, sys

p=subprocess.run(
    ["journalctl","--user","-u","prediction-codex-supervisor.service","-n","140","--no-pager"],
    text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20
)
s=(p.stdout or "").lower()

checks=[
    (41, ("unsupported model","model is not supported","gpt-6.1-sol","invalid model")),
    (42, ("stale pin","stale pins","pin mismatch","source changed","supervisor_source_changed")),
    (43, ("invalidargument","invalid argument","unrecognized arguments","usage: supervisor.py")),
    (44, ("usage limit","quota","rate limit","insufficient_quota","credits")),
    (45, ("codex: command not found","no such file or directory","codex-cli","codex cli")),
    (46, ("http 400","400 bad request","bad request")),
    (47, ("permission denied","permissionerror")),
    (48, ("timeout","timed out")),
]
for code, pats in checks:
    if any(x in s for x in pats):
        print(f"SUPERVISOR_DIAG_CLASS={code}")
        sys.exit(code)

print("SUPERVISOR_DIAG_CLASS=49")
sys.exit(49)
