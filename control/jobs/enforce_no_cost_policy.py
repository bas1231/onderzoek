from future import annotations

from pathlib import Path

ROOT = Path(file).resolve().parents[2]

POLICY = '''

## HARD NO-COST POLICY

Default: NO PAID ACTIONS.

No agent, worker, script, research task, build task, or execution component may perform, enable, invoke, recommend-as-an-execution-step, or authorize any action that may create monetary cost unless the user has given prior explicit permission for that specific cost-bearing action.

This includes, without limitation:

- paid APIs or metered API usage;
- cloud compute, VPS, hosted services, or subscriptions;
- paid datasets or data feeds;
- trades, orders, exchange fees, or transaction fees;
- wallet, crypto, blockchain, transfer, withdrawal, or gas costs;
- purchases, licenses, credits, deposits, or other paid services.

A general instruction to continue building or researching is not permission to incur cost.
Existing account access or credentials are not permission to incur cost.
A small amount is still a cost and requires explicit approval.

If there is uncertainty about whether an action can cost money, the system MUST fail closed, mark the action AWAITING_APPROVAL, and ask the user before execution.

No component may weaken, bypass, reinterpret, or silently override this rule.
'''

SENTINEL = '## HARD NO-COST POLICY'
TARGETS = [
 ROOT / 'AGENTS.md',
 ROOT / 'control' / 'LOCAL_EXECUTION_RULES.md',
]

for path in TARGETS:
 if not path.exists():
 raise SystemExit(f'REQUIRED FILE MISSING: {path.relative_to(ROOT)}')
 text = path.read_text(encoding='utf-8')
 if SENTINEL not in text:
 path.write_text(text.rstrip() + POLICY + '
', encoding='utf-8')

canonical = ROOT / 'control' / 'NO_COST_POLICY.md'
canonical.write_text(
 '# Prediction Research — No-Cost Policy
' + POLICY.split(SENTINEL, 1)[1].lstrip() + '
',
 encoding='utf-8',
)

for path in [*TARGETS, canonical]:
 text = path.read_text(encoding='utf-8')
 required = [
 'explicit permission',
 'fail closed',
 'paid APIs',
 'trades',
 'transaction fees',
 ]
 missing = [token for token in required if token not in text]
 if missing:
 raise SystemExit(f'POLICY VALIDATION FAILED for {path.relative_to(ROOT)}: {missing}')

print('PASS: hard no-cost policy installed')
print('PASS: AGENTS.md')
print('PASS: control/LOCAL_EXECUTION_RULES.md')
print('PASS: control/NO_COST_POLICY.md')
print('Default: fail closed; explicit user approval required before any cost-bearing action')
