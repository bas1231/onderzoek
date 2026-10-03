from __future__ import annotations
from pathlib import Path
import hashlib, sys

ROOT=Path.cwd()
PROD=Path.home()/"prediction_research_prod"
FILES=(
    "control/hourly/publication_wake.py",
    "control/hourly/git_checkpoint.py",
    "control/hourly/runtime_sync.py",
    "control/tampermonkey_multichat/continuation_manager.py",
)

def sha(p: Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def head()->str:
    raw=(PROD/".git/HEAD").read_text(encoding="utf-8").strip()
    if raw.startswith("ref: "):
        ref=raw[5:].strip()
        return (PROD/".git"/ref).read_text(encoding="utf-8").strip()
    return raw

def main()->int:
    expected=sys.argv[1]
    assert head()==expected
    for rel in FILES:
        assert sha(ROOT/rel)==sha(PROD/rel), rel
    checkpoint=(PROD/"control/hourly/git_checkpoint.py").read_text(encoding="utf-8")
    assert 'git("push"' not in checkpoint
    assert "publication.ensure_publication" in checkpoint
    wake=(PROD/"control/hourly/publication_wake.py").read_text(encoding="utf-8")
    assert "PREDICTION_GITHUB_PUBLICATION_V1" in wake
    assert "MAX_ENCODED_PAYLOAD = 4300" in wake
    print("PROD_PUBLICATION_VERIFY=PASS")
    print("PROD_HEAD="+expected)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
