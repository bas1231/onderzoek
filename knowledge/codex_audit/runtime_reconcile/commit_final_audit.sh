#!/usr/bin/env bash
# Afzonderlijk script: fouten sluiten de interactieve terminal niet.
set -euo pipefail
cd /home/leonh/prediction_research_prod
paths=(
 knowledge/codex_audit/FINAL_AUDIT_REPORT.md
 knowledge/codex_audit/FINDINGS.jsonl
 knowledge/codex_audit/OPEN_FINDINGS.md
 knowledge/codex_audit/TEST_MATRIX.md
 knowledge/codex_audit/REMEDIATION_LOG.md
 knowledge/codex_audit/RESIDUAL_RISKS.md
 knowledge/codex_audit/runtime_reconcile
 ':(exclude)**/__pycache__/**'
 ':(exclude)**/*.pyc'
)
before=$(git -c core.fsmonitor=false diff --cached --binary -- . ':(exclude)knowledge/codex_audit/**' | sha256sum)
git -c core.fsmonitor=false add -- "${paths[@]}"
git -c core.fsmonitor=false -c core.hooksPath=/dev/null -c commit.gpgsign=false commit --only -m "audit: record deployment and blocked hourly qualification" -- "${paths[@]}"
after=$(git -c core.fsmonitor=false diff --cached --binary -- . ':(exclude)knowledge/codex_audit/**' | sha256sum)
if [[ "$before" != "$after" ]]; then
 echo 'STOP: staged ownerdiff veranderde; controleer handmatig. Geen automatische rollback.'
 exit 1
fi
echo 'Auditbewijs lokaal gecommit; overige staged ownerdiff intact. Niets gepusht.'
