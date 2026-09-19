# Hourly Prediction Edge Watch — protocol

Doel: ieder uurrapport gebruikt `bas1231/onderzoek` als canonieke gedeelde kennislaag en rapporteert zowel externe research als nieuwe inhoud van andere agents/sessies.

## Verplichte volgorde per run

1. Lees `AGENTS.md`, `methodology/RESEARCH_PROTOCOL.md` en `negative_evidence/LEDGER.md`.
2. Lees het meest recente bestand in `meta/hourly_reports/` en neem `baseline_knowledge_head` als vorige Git-baseline.
3. Inspecteer alle commits en gewijzigde/nieuwe bestanden na die baseline. Negeer commits die uitsluitend bookkeeping in `meta/hourly_reports/` aanpassen.
4. Behandel commits die niet door de huidige sessie zijn geschreven als `other_session_or_agent_change`; GitHub-auteurschap alleen is onvoldoende om een specifieke agent te identificeren.
5. Vat betekenisvolle nieuwe Git-inhoud inhoudelijk samen en leg relaties/duplicaten/conflicten met bestaande records vast.
6. Voer daarna de actuele externe Prediction Edge Watch uit, Kalshi-first.
7. Schrijf duurzame nieuwe claims/hypotheses naar de passende `knowledge/`- of `negative_evidence/`-locatie met datum, status, provenance, required_data, falsification en execution_blockers waar relevant.
8. Bepaal daarna de laatste inhoudelijke commit-SHA vóór het auditrapport zelf en noteer die als `baseline_knowledge_head`.
9. Schrijf een auditrecord naar `meta/hourly_reports/YYYY-MM-DD_HHMM_TZ.md` wanneer er betekenisvolle nieuwe Git-inhoud of externe bevindingen zijn.

Deze baseline is bewust de laatste inhoudelijke commit vóór de rapport-write: een bestand kan zijn eigen commit-SHA niet stabiel bevatten. De volgende run scant na deze baseline en negeert pure hourly-report-bookkeeping.

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
