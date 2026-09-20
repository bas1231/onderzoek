from pathlib import Path

root=Path.cwd()
source=root/'control/jobs/smoke_asset_stdlib_ws_e342.py'
if not source.exists():
    raise SystemExit('known_good_stream_client_missing')
text=source.read_text(encoding='utf-8')
old='while time.monotonic()-start<45:'
new='while time.monotonic()-start<300:'
if text.count(old)!=1:
    raise SystemExit('duration_anchor_unexpected')
text=text.replace(old,new,1)
text=text.replace('ASSET_STDLIB_WS_SMOKE_PASS','ASSET_300S_STREAM_RECORD_PASS',1)
compile(text,str(source),'exec')
exec(compile(text,str(source),'exec'))
