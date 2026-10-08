# A→Z automatic 15-minute review retries

Status: REQUIRED FOR PRODUCTION — unverified until live canary
Date: 2026-10-08

All governed A→Z model review requests that use the `prediction-a2z-v4-model@<TASK_ID>.service` runner MUST have a corresponding enabled and active `prediction-a2z-v4-model@<TASK_ID>.timer` before the review is deemed successfully dispatched.

The existing timer template uses `OnCalendar=*:0/15` and `Persistent=true`. It must be installed and loaded, and the *exact current task instance* must be enabled and started. Enabling one prior model-task instance is not sufficient for future tasks. An active general supervisor timer likewise does not prove an A→Z instance is retried.

For all future candidates and all ASTRA_PREBUILD / ASTRA_POSTBUILD / SUPERVISOR requests, atomic dispatch acceptance requires:
1. Verify immutable request exists and matches model, phase and campaign.
2. Enable + start the matching timer instance through the capability-scoped projectexecutor.
3. Assert both `is-enabled` and `is-active` for the exact timer instance.
4. Start or hand off the model review only after the same bounded installation is successful.
5. Upon Codex usage exhaustion, leave task as `PAUSED_USAGE_LIMIT`, preserving run/thread and immutable request.
6. Each scheduled retry resumes via existing supervisor logic; never mark APPROVE or substitute models.
7. Once terminal completion is confirmed, disable the exact timer instance to avoid useless future launches, keeping the audit evidence.

Never rely on operator memory, task-specific manual setup, another chat session, or a timer for an earlier Sol task. Require an end-to-end canary before claiming all-future automatic reliability.

Safety: no modification of frozen bridge/router/executor, no paid action, live trade, wallet operation or autonomous WSL git push. `NO_PROVEN_EDGE` stays in force.
