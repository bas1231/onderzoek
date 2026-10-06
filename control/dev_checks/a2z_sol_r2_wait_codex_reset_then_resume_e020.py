import runpy,time
T=1791299820.0
w=max(0,T-time.time()+20)
if w>3600:
 print('WAIT_TOO_FAR',w); raise SystemExit(10)
if w: time.sleep(w)
print('CODEX_RESET_WINDOW_REACHED=1 RESUMING_SAME_IMMUTABLE_R2=1',flush=True)
runpy.run_path('control/dev_checks/a2z_sol_r2_resume_verify_e007.py',run_name='__main__')
