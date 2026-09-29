from __future__ import annotations

import hashlib
from pathlib import Path

root = Path.cwd().resolve()
out = root / ".runtime" / "bridge_demo_e001.txt"
out.parent.mkdir(parents=True, exist_ok=True)
payload = "Prediction bridge executed repository-owned Python in WSL.\n"
out.write_text(payload, encoding="utf-8")
readback = out.read_text(encoding="utf-8")

print(f"WSL_CODE_EXECUTION=PASS")
print(f"CWD={root}")
print(f"FILE={out}")
print(f"READBACK={readback.strip()}")
print(f"SHA256={hashlib.sha256(readback.encode('utf-8')).hexdigest()}")
