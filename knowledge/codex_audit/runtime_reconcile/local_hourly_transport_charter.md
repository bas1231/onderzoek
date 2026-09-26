# Bevroren bouwcharter — LOCAL-HOURLY-TRANSPORT-20260925
protocol_version: AUTONOMOUS_BUILD_PROTOCOL_V1
Doel: expliciete qualification_local transportselectie zonder Git-transport; echte request/responsecontracten behouden.
Scope/planned_paths: control/hourly/hourly_wake.py; control/hourly/local_ai_exchange.py; tests/hourly/test_local_ai_exchange.py.
Capabilities: lokale bronwijziging en geïsoleerde tests. Geen netwerk, diensten, financiën of remote-mutaties.
Acceptance: onbekende mode weigeren; local importeert nooit Git exchange; productie behoudt gedrag; echte contractvalidatie; ongeldige antwoorden zichtbaar; geen fictieve modelresponse of E2E-PASS.
Non-goals: browserdeployment, checkpoint, algemene audit, economische edge.
Independent_verification: root-agent beoordeelt diff en integratietests.
Rollback: eigen delta terugnemen na bronvergelijking; geen ownerreset.
Cleanup: uitsluitend tijdelijke pytest-fixtures; evidence behouden.
max_attempts: 3
governance_change: false
safety: no_push/no_trade/no_wallet/no_paid_api; procesconfinement valt onder parent-scope.

source_commit: 3c57e7b3ee16663203d80eb779943e2ec82cc53c
source_sha256 hourly_wake.py: 9fb8e1b268bf57601133da1f3e8235423d66913ffecdd9f3571ee50ed0311525
