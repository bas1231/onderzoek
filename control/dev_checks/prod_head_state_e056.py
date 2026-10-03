from __future__ import annotations
from pathlib import Path

PROD=Path.home()/"prediction_research_prod"

def git_dir():
    dot=PROD/".git"
    if dot.is_dir():
        return dot
    if dot.is_file():
        raw=dot.read_text(encoding="utf-8").strip()
        if raw.lower().startswith("gitdir:"):
            p=Path(raw.split(":",1)[1].strip())
            return (PROD/p).resolve() if not p.is_absolute() else p.resolve()
    raise RuntimeError("GIT_DIR_UNAVAILABLE")

def main():
    gd=git_dir()
    raw=(gd/"HEAD").read_text(encoding="utf-8").strip()
    branch="DETACHED"
    head=raw
    if raw.startswith("ref: "):
        ref=raw[5:].strip()
        branch=ref.rsplit("/",1)[-1]
        p=gd/ref
        if p.is_file():
            head=p.read_text(encoding="utf-8").strip()
        else:
            packed=gd/"packed-refs"
            if packed.is_file():
                for line in packed.read_text(encoding="utf-8").splitlines():
                    if line and not line.startswith("#") and not line.startswith("^"):
                        sha,name=line.split(" ",1)
                        if name==ref:
                            head=sha
                            break
    print(f"PROD_HEAD_STATE|branch={branch}|head={head}|gitdir={gd}",flush=True)
    return 42

if __name__=="__main__":
    raise SystemExit(main())
