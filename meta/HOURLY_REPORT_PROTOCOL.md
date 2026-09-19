# Hourly Prediction Edge Watch — protocol

Doel: ieder uurrapport gebruikt `bas1231/onderzoek` als canonieke gedeelde kennislaag en rapporteert zowel externe research als nieuwe inhoud van andere agents/sessies.

## Verplichte volgorde per run

1. Lees `AGENTS.md`, `methodology/RESEARCH_PROTOCOL.md` en `negative_evidence/LEDGER.md`.
2. Lees het meest recente bestand in `meta/hourly_reports/` en neem `baseline_head_after_run` als vorige Git-baseline.
3. Inspecteer alle commits en gewijzigde/nieuwe bestanden na die baseline.
4. Behandel commits die niet door de huidige sessie zijn geschreven als `other_session_or_agent_change`; GitHub-auteurschap alleen is onvoldoende om een specifieke agent te identificeren.
5. Vat betekenisvolle nieuwe Git-inhoud inhoudelijk samen en leg relaties/duplicaten/conflicten met bestaande records vast.
6. Voer daarna de actuele externe Prediction Edge Watch uit, Kalshi-first.
7. Schrijf duurzame nieuwe claims/hypotheses naar de passende `knowledge/`- of `negative_evidence/`-locatie met datum, status, provenance, required_data, falsification en execution_blockers waar relevant.
8. Schrijf altijd een auditrecord van de run naar `meta/hourly_reports/YYYY-MM-DD_HHMM_TZ.md` wanneer er betekenisvolle nieuwe Git-inhoud of externe bevindingen zijn.
9. Noteer in dat record de HEAD-SHA na alle writes als `baseline_head_after_run`, zodat de volgende run alleen de echte delta hoeft te inspecteren.

## Rapportindeling

### A — Nieuwe Git-inhoud van andere sessies/agents
- commit(s)
- bestand(en)
- inhoudelijke betekenis
- relatie tot bestaande hypotheses
- eventuele conflicten/deduplicatie

### B — Nieuwe externe research
- bron/provenance
- nieuw versus duplicaat
- bewijsniveau/status
- mechanisme
- required_data
- falsificatietest
- execution-risico
- relatie met bestaande hypotheses

### C — Status
Economische default blijft `NO_PROVEN_EDGE` totdat alle gates uit `methodology/RESEARCH_PROTOCOL.md` zijn gehaald.

## Veiligheidsgrens
Geen operationele research voor fraude, marktmanipulatie, KYC-/geo-omzeiling, sabotage, credentialmisbruik of software-exploitatie. Publiek gedocumenteerde securityproblemen mogen defensief als risico/negative evidence worden vastgelegd zonder misbruikinstructies.
