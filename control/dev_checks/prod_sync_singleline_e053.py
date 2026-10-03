from __future__ import annotations
import contextlib, io, runpy

def main():
    buf=io.StringIO()
    with contextlib.redirect_stdout(buf):
        runpy.run_path("control/dev_checks/prod_sync_compact_diag_e051.py", run_name="__main__")
    print("PROD_SYNC_DIAG|"+buf.getvalue().strip().replace("\n","|"), flush=True)
    return 42

if __name__=="__main__":
    raise SystemExit(main())
