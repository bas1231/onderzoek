from __future__ import annotations
import contextlib, io, runpy

def main():
    mod=runpy.run_path("control/dev_checks/prod_sync_compact_diag_e051.py")
    buf=io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc=mod["main"]()
    print("PROD_SYNC_DIAG|rc="+str(rc)+"|"+buf.getvalue().strip().replace("\n","|"), flush=True)
    return 42

if __name__=="__main__":
    raise SystemExit(main())
