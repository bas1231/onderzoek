from pathlib import Path
import json

home=Path.home()
event="1791038937-3ce66aaea326"
receipt=f"RESULT-RECEIPT-{event}"
state=home/".local/state/prediction-command-bus/tasks"/f"{receipt}.json"
bridge=home/".local/share/prediction-chat-bridge"

status="MISSING"
reason=""
if state.is_file():
    try:
        obj=json.loads(state.read_text(encoding="utf-8"))
        status=str(obj.get("status") or "")
        reason=str(obj.get("reason") or "")
    except Exception as exc:
        status=f"INVALID:{type(exc).__name__}"

print(
    "RESULT_RECEIPT_DIAG"
    f"|receipt_state={status}"
    f"|reason={reason.replace('|','/')[:120]}"
    f"|inflight={(bridge/'inflight'/f'{event}.json').is_file()}"
    f"|sent={(bridge/'sent'/f'{event}.json').is_file()}",
    flush=True,
)
raise SystemExit(42)
