# Prediction bridge three-port runtime probe

Started UTC: 2026-09-24T14:03:54.178774+00:00
Finished UTC: 2026-09-24T14:04:24.543567+00:00
Probe duration: 30 seconds, ~4 samples/sec.

## Port summary
- `8765`: `{"http_200": 119, "http_statuses": {"200": 119}, "http_unreachable": 0, "samples": 119, "tcp_fail": 0, "tcp_ok": 119}`
- `8766`: `{"http_200": 119, "http_statuses": {"200": 119}, "http_unreachable": 0, "samples": 119, "tcp_fail": 0, "tcp_ok": 119}`
- `8767`: `{"http_200": 119, "http_statuses": {"200": 119}, "http_unreachable": 0, "samples": 119, "tcp_fail": 0, "tcp_ok": 119}`

## systemd before/after
- `prediction-chat-wake.service` before: `{"ActiveEnterTimestamp": "Thu 2026-09-24 15:52:46 CEST", "ActiveState": "active", "ExecMainStatus": "0", "InactiveEnterTimestamp": "", "MainPID": "305", "NRestarts": "0", "Result": "success", "SubState": "running", "rc": "0"}`
- `prediction-chat-wake.service` after: `{"ActiveEnterTimestamp": "Thu 2026-09-24 15:52:46 CEST", "ActiveState": "active", "ExecMainStatus": "0", "InactiveEnterTimestamp": "", "MainPID": "305", "NRestarts": "0", "Result": "success", "SubState": "running", "rc": "0"}`
- `prediction-chat-command.service` before: `{"ActiveEnterTimestamp": "Thu 2026-09-24 15:52:46 CEST", "ActiveState": "active", "ExecMainStatus": "0", "InactiveEnterTimestamp": "", "MainPID": "299", "NRestarts": "0", "Result": "success", "SubState": "running", "rc": "0"}`
- `prediction-chat-command.service` after: `{"ActiveEnterTimestamp": "Thu 2026-09-24 15:52:46 CEST", "ActiveState": "active", "ExecMainStatus": "0", "InactiveEnterTimestamp": "", "MainPID": "299", "NRestarts": "0", "Result": "success", "SubState": "running", "rc": "0"}`
- `prediction-chat-router.service` before: `{"ActiveEnterTimestamp": "Thu 2026-09-24 15:52:46 CEST", "ActiveState": "active", "ExecMainStatus": "0", "InactiveEnterTimestamp": "", "MainPID": "301", "NRestarts": "0", "Result": "success", "SubState": "running", "rc": "0"}`
- `prediction-chat-router.service` after: `{"ActiveEnterTimestamp": "Thu 2026-09-24 15:52:46 CEST", "ActiveState": "active", "ExecMainStatus": "0", "InactiveEnterTimestamp": "", "MainPID": "301", "NRestarts": "0", "Result": "success", "SubState": "running", "rc": "0"}`

## Classification
- 8767 stayed reachable throughout this 30-second window.
- 8766 stayed reachable throughout this 30-second window.
- 8765 stayed reachable throughout this 30-second window.

## Recent service logs

### prediction-chat-wake.service
```text
2026-09-24T16:04:04+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:04] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:04+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:04] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:04+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:04] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:04+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:04] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:05+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:05] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:05+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:05] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:05+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:05] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:05+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:05] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:06+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:06] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:06+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:06] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:06+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:06] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:06+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:06] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:07+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:07] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:07+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:07] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:07+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:07] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:07+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:07] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:08+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:08] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:08+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:08] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:08+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:08] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:08+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:08] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:09+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:09] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:09+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:09] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:09+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:09] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:09+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:09] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:10+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:10] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:10+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:10] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:10+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:10] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:10+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:10] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:11+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:11] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:11+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:11] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:11+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:11] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:11+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:11] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:12+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:12] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:12+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:12] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:12+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:12] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:12+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:12] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:13+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:13] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:13+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:13] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:13+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:13] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:13+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:13] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:14+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:14] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:14+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:14] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:14+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:14] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:14+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:14] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:15+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:15] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:15+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:15] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:15+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:15] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:15+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:15] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:16+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:16] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:16+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:16] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:16+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:16] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:17+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:17] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:17+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:17] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:17+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:17] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:17+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:17] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:18+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:18] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:18+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:18] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:18+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:18] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:18+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:18] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:19+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:19] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:19+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:19] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:19+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:19] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:19+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:19] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:20+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:20] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:20+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:20] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:20+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:20] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:20+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:20] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:21+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:21] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:21+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:21] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:21+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:21] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:21+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:21] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:22+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:22] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:22+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:22] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:22+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:22] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:22+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:22] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:23+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:23] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:23+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:23] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:23+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:23] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:23+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:23] "GET /health HTTP/1.1" 200 -
2026-09-24T16:04:24+02:00 Strix python3[305]: 127.0.0.1 - - [24/Sep/2026 16:04:24] "GET /health HTTP/1.1" 200 -
```

### prediction-chat-command.service
```text
-- No entries --
```

### prediction-chat-router.service
```text
2026-09-24T15:55:40+02:00 Strix python3[301]: 127.0.0.1 - - [24/Sep/2026 15:55:40] "POST /command HTTP/1.1" 200 -
2026-09-24T15:58:56+02:00 Strix python3[301]: 127.0.0.1 - - [24/Sep/2026 15:58:56] "POST /command HTTP/1.1" 200 -
2026-09-24T16:03:50+02:00 Strix python3[301]: 127.0.0.1 - - [24/Sep/2026 16:03:50] "POST /command HTTP/1.1" 200 -
```
