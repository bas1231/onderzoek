from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

candidates = []
system_pytest = shutil.which("pytest")
if system_pytest:
    candidates.append(("pytest_executable", system_pytest, [system_pytest, "--version"]))

for label, path in [
    ("fg_assistent_venv", Path("/home/leonh/fg_assistent/.venv/bin/python")),
    ("prediction_research_venv", Path("/home/leonh/prediction_research/.venv/bin/python")),
    ("prediction_prod_venv", Path("/home/leonh/prediction_research_prod/.venv/bin/python")),
    ("user_venv", Path("/home/leonh/.venv/bin/python")),
]:
    if path.is_file():
        candidates.append((label, str(path), [str(path), "-m", "pytest", "--version"]))

results = []
for label, path, argv in candidates:
    try:
        cp = subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=15)
        results.append({"label": label, "path": path, "rc": cp.returncode, "output": (cp.stdout or "").strip()[:300]})
        if cp.returncode == 0:
            print("PYTEST_PROVIDER=" + label)
            print("PYTEST_PATH=" + path)
            print("PYTEST_VERSION=" + (cp.stdout or "").strip().replace("\n", " ")[:300])
            raise SystemExit({
                "pytest_executable": 71,
                "fg_assistent_venv": 72,
                "prediction_research_venv": 73,
                "prediction_prod_venv": 74,
                "user_venv": 75,
            }[label])
    except Exception as exc:
        results.append({"label": label, "path": path, "error": type(exc).__name__})

print("PYTEST_PROVIDER=NONE")
print(json.dumps(results, separators=(",", ":")))
raise SystemExit(76)
