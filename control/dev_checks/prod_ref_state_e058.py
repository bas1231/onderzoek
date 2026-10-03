from __future__ import annotations
from pathlib import Path

PROD=Path.home()/"prediction_research_prod"

def git_dir():
    dot=PROD/".git"
    if dot.is_dir():
        return dot
    raw=dot.read_text(encoding="utf-8").strip()
    p=Path(raw.split(":",1)[1].strip())
    return (PROD/p).resolve() if not p.is_absolute() else p.resolve()

def ref_sha(gd: Path, ref: str):
    p=gd/ref
    if p.is_file():
        return p.read_text(encoding="utf-8").strip()
    packed=gd/"packed-refs"
    if packed.is_file():
        for line in packed.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#") or line.startswith("^"):
                continue
            sha,name=line.split(" ",1)
            if name==ref:
                return sha
    return "MISSING"

def main():
    gd=git_dir()
    raw=(gd/"HEAD").read_text(encoding="utf-8").strip()
    branch=raw[5:].rsplit("/",1)[-1] if raw.startswith("ref: ") else "DETACHED"
    head=ref_sha(gd,raw[5:].strip()) if raw.startswith("ref: ") else raw
    main_ref=ref_sha(gd,"refs/heads/main")
    print(f"PROD_REF_STATE|branch={branch}|head={head}|main={main_ref}|equal={str(head==main_ref).lower()}",flush=True)
    return 42

if __name__=="__main__":
    raise SystemExit(main())
