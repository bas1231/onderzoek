# Polymarket — resolution is niet hetzelfde als settlement

Datum: 2026-09-21
Status: `RESEARCH_POSITIVE / SETTLEMENT-RISK EVIDENCE / NO_PROVEN_EDGE`

## Nieuwe evidence
Een academische preprint van 14 september 2026 reconstrueert Polymarket-oracle-adjudicatie event-sourced en maakt een belangrijk onderscheid tussen request creation, proposal, dispute/reset, oracle finality, adapter terminality en uiteindelijke holder realization. De populatie bevat 185.550 adapter-question instances en 504.332 gedecodeerde oracle-lifecycle events. De auteurs benadrukken expliciet dat request age niet hetzelfde is als semantic resolution age en dat externe bronpublicatie/contractual-decidability clocks populatiebreed niet gemeten zijn.

Bron: Maksym Nechepurenko, *Resolution Is Not Settlement, Part I: Oracle Adjudication and Semantic Governance on Polymarket*, arXiv:2609.15368, 2026-09-14.

## Betekenis voor de factory
- `settlement` moet adjudication, oracle finality, adapter terminality en realization als afzonderlijke toestanden behandelen.
- Een waargenomen proposal of oracle-event is op zichzelf geen bewijs dat payout/funds al economisch beschikbaar zijn.
- Latencyonderzoek mag oracle-mechanism timestamps niet substitueren voor de ontbrekende external-source publication / contractual-decidability clock.
- Dit versterkt de bestaande execution-first eis dat finality en capital-lock expliciet in `net_locked_edge` worden opgenomen.

## Chief Falsifier
Deze studie bewijst geen exploiteerbare settlement-lag. De grote verschillen in proposal timing zijn descriptief en volgens de auteur niet causaal. Metadata-linkage is bovendien slechts 56,07% voor exact stable-ID matching; unmatched cases mogen niet worden ingevuld met aannames.

## Besluit
Duurzame methodologische/settlement evidence, maar geen candidate promotion. Economische status blijft `NO_PROVEN_EDGE`.
