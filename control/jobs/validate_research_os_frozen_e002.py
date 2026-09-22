from __future__ import annotations

from pathlib import Path

OLD_HEAD = "a0d9ba659e529c0cfc9e2eb8e2c38342312c0539"
NEW_HEAD = "c0716bfbe6299d1fddbca2bb8f0bf4c872dd127a"

source_path = Path(__file__).with_name("validate_research_os_frozen_e001.py")
source = source_path.read_text(encoding="utf-8")

if source.count(OLD_HEAD) != 1:
    raise RuntimeError(
        f"fail closed: expected exactly one frozen-head pin {OLD_HEAD}, "
        f"found {source.count(OLD_HEAD)}"
    )

source = source.replace(OLD_HEAD, NEW_HEAD)
compiled = compile(source, str(source_path), "exec")
exec(compiled, {"__name__": "__main__", "__file__": str(source_path)})
