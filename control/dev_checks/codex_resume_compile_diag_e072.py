from __future__ import annotations
import py_compile
from pathlib import Path

target = Path("control/codex_supervisor/supervisor.py")
try:
    py_compile.compile(str(target), doraise=True)
except Exception as exc:
    text = str(exc).replace("\n", " | ").replace("\r", " ")
    print(f"CODEX_RESUME_COMPILE_DIAG|status=FAIL|type={type(exc).__name__}|detail={text[:900]}", flush=True)
    raise SystemExit(42)
print("CODEX_RESUME_COMPILE_DIAG|status=PASS", flush=True)
raise SystemExit(0)
