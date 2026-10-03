from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path
import zlib

ROOT=Path.cwd()
MODULE=ROOT/"control/hourly/publication_wake.py"

def load():
    spec=importlib.util.spec_from_file_location("publication_acceptance",MODULE)
    assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

class FakeContinuation:
    def __init__(self):
        self.calls=[]
    def ids_for(self,source_task_id):
        digest=hashlib.sha256(source_task_id.encode()).hexdigest()[:24]
        return {"continuation_id":"CONT-"+digest}
    def continuation_path(self,data_dir,continuation_id):
        return Path(data_dir)/"continuations"/f"{continuation_id}.json"
    def start_external_continuation(self,**kwargs):
        self.calls.append(kwargs)
        ids=self.ids_for(kwargs["source_task_id"])
        p=self.continuation_path(kwargs["data_dir"],ids["continuation_id"])
        p.parent.mkdir(parents=True,exist_ok=True)
        if not p.exists():
            p.write_text(json.dumps({"state":"CONTINUE_REQUESTED"})+"\n",encoding="utf-8")
        return {"continuation_id":ids["continuation_id"],"state":"CONTINUE_REQUESTED"}

def configure(mod,tmp):
    bridge=tmp/"bridge"
    routes=bridge/"routes"
    routes.mkdir(parents=True)
    route_task_id="ROUTE-TEST-1234"
    (bridge/"autobuild_control_route.json").write_text(json.dumps({
        "schema":"PREDICTION_AUTOBUILD_ROUTE_V1",
        "route_task_id":route_task_id,
    }),encoding="utf-8")
    (routes/f"{route_task_id}.json").write_text(json.dumps({
        "task_id":route_task_id,
        "chat_id":"chat-test-1234",
    }),encoding="utf-8")
    fake=FakeContinuation()
    mod.BRIDGE_DATA=bridge
    mod.ROUTE_CONFIG=bridge/"autobuild_control_route.json"
    mod.ROUTES=routes
    mod.AUDIT_ROOT=tmp/"audit"
    mod._load_continuation=lambda: fake
    return fake

def main():
    mod=load()
    with tempfile.TemporaryDirectory() as td:
        tmp=Path(td)
        fake=configure(mod,tmp)

        denied=tmp/"knowledge/raw/x.json"
        denied.parent.mkdir(parents=True)
        denied.write_text("{}",encoding="utf-8")
        try:
            mod.ensure_publication("knowledge/raw/x.json",root=tmp)
            raise AssertionError("denied path accepted")
        except mod.PublicationBlocked:
            pass

        rel="knowledge/candidates/test.json"
        target=tmp/rel
        target.parent.mkdir(parents=True,exist_ok=True)
        raw=b'{"candidate_id":"TEST","status":"RESULT_READY"}\n'
        target.write_bytes(raw)

        first=mod.ensure_publication(rel,root=tmp)
        second=mod.ensure_publication(rel,root=tmp)
        assert first["status"]=="CONTINUATION_CREATED"
        assert first["new_continuation"] is True
        assert second["new_continuation"] is False
        assert first["source_task_id"]==second["source_task_id"]

        context=fake.calls[0]["context_message"]
        assert f"path={rel}" in context
        payload_line=next(x for x in context.splitlines() if x.startswith("payload="))
        encoded=payload_line.split("=",1)[1]
        assert zlib.decompress(base64.b64decode(encoded))==raw
        assert fake.calls[0]["source_kind"]=="GITHUB_PUBLICATION"

        large_rel="knowledge/candidates/large.json"
        large=tmp/large_rel
        tokens=[hashlib.sha256(str(i).encode()).hexdigest() for i in range(500)]
        large.write_text(json.dumps({"tokens":tokens},separators=(",",":"))+"\n",encoding="utf-8")
        before=len(fake.calls)
        result=mod.ensure_publication(large_rel,root=tmp)
        assert result["status"]=="OVERSIZED_LOCAL_ONLY"
        assert len(fake.calls)==before

    print("PUBLICATION_ACCEPTANCE=PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
