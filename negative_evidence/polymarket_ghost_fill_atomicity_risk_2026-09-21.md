# Polymarket — ghost-filled order / atomicity gap

Datum: 2026-09-21
Status: `NEGATIVE_EVIDENCE / NON_EXECUTABLE INTELLIGENCE / NO_PROVEN_EDGE`

Een academische preprint van 15 september 2026 beschrijft een atomicity gap tussen off-chain order acceptance/matching en on-chain settlement bij non-custodial prediction markets, met Polymarket als case study. De studie analyseert 1,8 miljoen reverted transactions over 2025-08-12 t/m 2026-05-22 en beschrijft dat orders tussen off-chain match en on-chain settlement ongeldig kunnen worden.

Bron: Zhiyang Chen, Fan Long, Zhendong Su, *Ghost-Filled Orders: Detecting and Testing Atomicity Violations in Non-Custodial Prediction Markets*, arXiv:2609.17902, 2026-09-15.

## Factory-conclusie
Dit is execution-risk en geen toegestane execution-lane. De factory bouwt of test geen strategie die een dergelijke atomicity gap operationeel misbruikt. Voor legitieme replay/edge-claims betekent dit dat een off-chain fill-indicatie niet automatisch als gerealiseerde on-chain fill mag worden geboekt; settlement/revert-status moet waar relevant worden bevestigd.

## Pre-Build Killer
`KILL` als strategy-warrant: geen strategycode, geen exploitatie, geen economische promotie. Alleen bewaren als negative evidence voor fill/settlement-modellering.

Economische status: `NO_PROVEN_EDGE`.
