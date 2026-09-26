# BUILD-QUEUE-DRAIN-20260926 — vooraf bevroren

Doel: bestaande Director-candidates selecteren wanneer de canonical SQLite AI-queue geen runnable werk bevat; eenmaal per inputversie uitvoeren en resultaat/volgende actie duurzaam toepassen. Geen tweede queue. Scope: supervisor.py, nieuwe candidate_dispatch.py, gerichte tests en configuratie/evidence onder knowledge/codex_runtime. Basis 398f149. Owner-candidatebestanden/index blijven ongewijzigd.

Acceptance: bestaande priority/aging; COMPLETE/RUNNING/PARKED/WAITING/WATCH/human/financial gates overslaan; single-worker; stabiele inputhash-ID; durable selectie vóór invocation; crash/resume/quota behouden; geen dubbele complete taak; echte timer-canary zonder handmatige enqueue; lege queue IDLE/QUEUE_EMPTY. Resultaatapplicatie betekent gevalideerd kandidaatbesluit in bestaande task-run evidence, nooit ownerbestand overschrijven of modelcode uitvoeren. Geen tradingresearch handmatig, push, kosten of resets.

Verificatie: gerichte adversarial tests en echte timer. Rollback uitsluitend eigen codewijziging, geen ownerreset. Cleanup tijdelijke testfixtures; permanente timers blijven. Max3 pogingen per concrete blocker. Geen nieuwe globale audit/PASS-claim. Machinecontract vóór implementatie gevalideerd en opgeslagen in QUEUE_DRAIN_GOVERNANCE.json.
