# Bridge efficiency benchmark

Task: `DEV-PRED-BRIDGE-EFFICIENCY-BENCH-E006`
Started UTC: `2026-09-24T14:25:19.496292+00:00`
Duration seconds: `60.044`
Route→benchmark start: `3890.503 ms`
Sample cycles: `294`

## Latency and reliability
- `8765` TCP: `{"fail": 0, "max_ms": 1.249, "mean_ms": 0.284, "n": 294, "p50_ms": 0.273, "p95_ms": 0.396, "p99_ms": 0.658}`
- `8765` HTTP /health: `{"fail": 0, "max_ms": 18.649, "mean_ms": 1.471, "n": 294, "p50_ms": 1.399, "p95_ms": 1.734, "p99_ms": 2.02, "statuses": {"200": 294}}`
- `8766` TCP: `{"fail": 0, "max_ms": 0.235, "mean_ms": 0.125, "n": 294, "p50_ms": 0.13, "p95_ms": 0.154, "p99_ms": 0.221}`
- `8766` HTTP /health: `{"fail": 0, "max_ms": 1.189, "mean_ms": 0.836, "n": 294, "p50_ms": 0.82, "p95_ms": 0.99, "p99_ms": 1.071, "statuses": {"200": 294}}`
- `8767` TCP: `{"fail": 0, "max_ms": 0.345, "mean_ms": 0.125, "n": 294, "p50_ms": 0.119, "p95_ms": 0.173, "p99_ms": 0.267}`
- `8767` HTTP /health: `{"fail": 0, "max_ms": 1.16, "mean_ms": 0.842, "n": 294, "p50_ms": 0.831, "p95_ms": 0.998, "p99_ms": 1.076, "statuses": {"200": 294}}`

## Service stability
- `prediction-chat-wake.service` before: `{"ActiveEnterTimestamp": "Thu 2026-09-24 15:52:46 CEST", "ActiveState": "active", "CPUUsageNSec": "8747806000", "ExecMainStatus": "0", "MainPID": "305", "MemoryCurrent": "12402688", "NRestarts": "0", "Result": "success", "SubState": "running", "rc": "0"}`
- `prediction-chat-wake.service` after: `{"ActiveEnterTimestamp": "Thu 2026-09-24 15:52:46 CEST", "ActiveState": "active", "CPUUsageNSec": "9633972000", "ExecMainStatus": "0", "MainPID": "305", "MemoryCurrent": "14069760", "NRestarts": "0", "Result": "success", "SubState": "running", "rc": "0"}`
- `prediction-chat-wake.service` stable: `True`
- `prediction-chat-command.service` before: `{"ActiveEnterTimestamp": "Thu 2026-09-24 15:52:46 CEST", "ActiveState": "active", "CPUUsageNSec": "2726623000", "ExecMainStatus": "0", "MainPID": "299", "MemoryCurrent": "44982272", "NRestarts": "0", "Result": "success", "SubState": "running", "rc": "0"}`
- `prediction-chat-command.service` after: `{"ActiveEnterTimestamp": "Thu 2026-09-24 15:52:46 CEST", "ActiveState": "active", "CPUUsageNSec": "3754493000", "ExecMainStatus": "0", "MainPID": "299", "MemoryCurrent": "49004544", "NRestarts": "0", "Result": "success", "SubState": "running", "rc": "0"}`
- `prediction-chat-command.service` stable: `True`
- `prediction-chat-router.service` before: `{"ActiveEnterTimestamp": "Thu 2026-09-24 15:52:46 CEST", "ActiveState": "active", "CPUUsageNSec": "632900000", "ExecMainStatus": "0", "MainPID": "301", "MemoryCurrent": "12873728", "NRestarts": "0", "Result": "success", "SubState": "running", "rc": "0"}`
- `prediction-chat-router.service` after: `{"ActiveEnterTimestamp": "Thu 2026-09-24 15:52:46 CEST", "ActiveState": "active", "CPUUsageNSec": "1059824000", "ExecMainStatus": "0", "MainPID": "301", "MemoryCurrent": "14036992", "NRestarts": "0", "Result": "success", "SubState": "running", "rc": "0"}`
- `prediction-chat-router.service` stable: `True`

## Queue/backlog
- Before: `{"outbox": 13, "sent": 188}`
- After: `{"outbox": 13, "sent": 188}`
- Route record: `{"chat_id": "chat-c-d2389a5c-10", "created_at_unix": 1790259915.6057804, "task_id": "DEV-PRED-BRIDGE-EFFICIENCY-BENCH-E006", "version": 1}`
- Route contains consumer_id: `False`

## Classification
- PASS: no TCP/HTTP failures and no bridge service restart/state transition during the benchmark.
- Observed router route creation → benchmark process start: 3890.5 ms.
- Worst /health p95 across ports: 1.734 ms.
- Remaining design risk: route record contains chat_id but no consumer_id, so multiple tabs on one chat can still compete for delivery leases.
- Result-event creation and browser-visible ACK are measured in the follow-up audit after this task result exists.
