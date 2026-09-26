# Bridge efficiency benchmark

Task: `DEV-PRED-BRIDGE-EFFICIENCY-POSTFIX-E016`
Started UTC: `2026-09-24T15:12:33.054562+00:00`
Duration seconds: `60.215`
Route→benchmark start: `2106.625 ms`
Sample cycles: `295`

## Latency and reliability
- `8765` TCP: `{"fail": 0, "max_ms": 1.417, "mean_ms": 0.288, "n": 295, "p50_ms": 0.269, "p95_ms": 0.418, "p99_ms": 0.607}`
- `8765` HTTP /health: `{"fail": 0, "max_ms": 18.373, "mean_ms": 1.493, "n": 295, "p50_ms": 1.427, "p95_ms": 1.816, "p99_ms": 2.136, "statuses": {"200": 295}}`
- `8766` TCP: `{"fail": 0, "max_ms": 1.06, "mean_ms": 0.131, "n": 295, "p50_ms": 0.13, "p95_ms": 0.156, "p99_ms": 0.241}`
- `8766` HTTP /health: `{"fail": 0, "max_ms": 1.539, "mean_ms": 0.852, "n": 295, "p50_ms": 0.838, "p95_ms": 1.053, "p99_ms": 1.153, "statuses": {"200": 295}}`
- `8767` TCP: `{"fail": 0, "max_ms": 0.288, "mean_ms": 0.123, "n": 295, "p50_ms": 0.124, "p95_ms": 0.176, "p99_ms": 0.257}`
- `8767` HTTP /health: `{"fail": 0, "max_ms": 1.529, "mean_ms": 0.857, "n": 295, "p50_ms": 0.838, "p95_ms": 1.06, "p99_ms": 1.489, "statuses": {"200": 295}}`

## Service stability
- `prediction-chat-wake.service` before: `{"ActiveEnterTimestamp": "Thu 2026-09-24 17:10:48 CEST", "ActiveState": "active", "CPUUsageNSec": "714159000", "ExecMainStatus": "0", "MainPID": "9034", "MemoryCurrent": "13570048", "NRestarts": "1", "Result": "success", "SubState": "running", "rc": "0"}`
- `prediction-chat-wake.service` after: `{"ActiveEnterTimestamp": "Thu 2026-09-24 17:10:48 CEST", "ActiveState": "active", "CPUUsageNSec": "1614572000", "ExecMainStatus": "0", "MainPID": "9034", "MemoryCurrent": "14848000", "NRestarts": "1", "Result": "success", "SubState": "running", "rc": "0"}`
- `prediction-chat-wake.service` stable: `True`
- `prediction-chat-command.service` before: `{"ActiveEnterTimestamp": "Thu 2026-09-24 15:52:46 CEST", "ActiveState": "active", "CPUUsageNSec": "6997108000", "ExecMainStatus": "0", "MainPID": "299", "MemoryCurrent": "55742464", "NRestarts": "0", "Result": "success", "SubState": "running", "rc": "0"}`
- `prediction-chat-command.service` after: `{"ActiveEnterTimestamp": "Thu 2026-09-24 15:52:46 CEST", "ActiveState": "active", "CPUUsageNSec": "8025148000", "ExecMainStatus": "0", "MainPID": "299", "MemoryCurrent": "57057280", "NRestarts": "0", "Result": "success", "SubState": "running", "rc": "0"}`
- `prediction-chat-command.service` stable: `True`
- `prediction-chat-router.service` before: `{"ActiveEnterTimestamp": "Thu 2026-09-24 17:10:48 CEST", "ActiveState": "active", "CPUUsageNSec": "106238000", "ExecMainStatus": "0", "MainPID": "9032", "MemoryCurrent": "13426688", "NRestarts": "1", "Result": "success", "SubState": "running", "rc": "0"}`
- `prediction-chat-router.service` after: `{"ActiveEnterTimestamp": "Thu 2026-09-24 17:10:48 CEST", "ActiveState": "active", "CPUUsageNSec": "539400000", "ExecMainStatus": "0", "MainPID": "9032", "MemoryCurrent": "14573568", "NRestarts": "1", "Result": "success", "SubState": "running", "rc": "0"}`
- `prediction-chat-router.service` stable: `True`

## Queue/backlog
- Before: `{"outbox": 13, "sent": 198}`
- After: `{"outbox": 13, "sent": 198}`
- Route record: `{"chat_id": "chat-c-d2389a5c-10", "consumer_id": "tab-muf6v3ik-hv3gtbxg", "created_at_unix": 1790262750.9479325, "task_id": "DEV-PRED-BRIDGE-EFFICIENCY-POSTFIX-E016", "version": 2}`
- Route contains consumer_id: `True`

## Classification
- PASS: no TCP/HTTP failures and no bridge service restart/state transition during the benchmark.
- Observed router route creation → benchmark process start: 2106.6 ms.
- Worst /health p95 across ports: 1.816 ms.
- Result-event creation and browser-visible ACK are measured in the follow-up audit after this task result exists.
