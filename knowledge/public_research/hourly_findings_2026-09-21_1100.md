# Hourly finding — 2026-09-21 11:00 CEST

Status: RESEARCH_ONLY / NO_PROVEN_EDGE

## Nieuwe evidence

ProphetX kondigde op 2026-09-10 een integratie met Agg Market aan waarmee 100% van zijn contractcatalogus via Solana toegankelijk is. De primaire aankondiging zegt expliciet dat deze extra access channel de voorwaarden, execution en settlement framework van ProphetX-listed contracts niet verandert. Agg kan deze route standalone of via bredere liquidity APIs aanbieden.

Een secundaire technische beschrijving meldt dat Agg bij aankoop on-chain capital escrowt, de corresponderende positie op ProphetX neemt en vervolgens een SPL-token mint; verkoop/claim zou het token burnen en de onderliggende ProphetX-positie/verrekening volgen. Deze precieze custody/tokenization-flow moet nog tegen Agg's eigen technische documentatie worden gereproduceerd voordat hij als FACT_VERIFIED geldt.

## Specialist-routing

- scout: nieuwe venue-distribution/access-layer evidence; niet eerder aangetroffen in Git-memory.
- microstructure: een Agg/Solana quote of tokenprijs is niet automatisch dezelfde execution surface als ProphetX. Voor economische vergelijking zijn contemporaneous fillable prices, routing latency, fees, size, inventory/hedge timing en failure modes aan beide lagen nodig.
- algebra: een tokenized claim op een ProphetX-position is geen tweede onafhankelijke payoutbron. Een prijsverschil kan alleen kandidaat-edge zijn na bewijs van exacte entitlement/equivalence en netto executable conversion/redemption.
- settlement: underlying ProphetX contract terms en settlement blijven volgens de primaire aankondiging onveranderd; token claim/redemption vormt een extra finality/custody-laag en mag niet met underlying settlement worden samengevouwen.
- behavioral: GEEN NIEUWE UITKOMST.
- informed_flow: GEEN NIEUWE UITKOMST.
- weather_twc: GEEN NIEUWE UITKOMST.

## Pre-Build Killer

Geen build warrant. Er is nog geen point-in-time paired executable observation, geen onafhankelijk geverifieerde tokenization/redemption semantics en geen volledige fee/latency/failure accounting.

## Chief Falsifier

Voor een eventuele cross-representation kandidaat moeten minimaal worden aangevallen:
1. claim-equivalence/custody en redemption-finality;
2. simultane executable pricing en beschikbare size;
3. alle routing/network/venue fees, latency, legging en temporary inventory risk.

Independent Reproducer: niet geactiveerd; geen positieve economische instance.

## Besluit

Mechanism lead bewaren, geen persistent economic candidate aanmaken. Signal edge: niet aangetoond. Market edge: niet aangetoond. Execution edge: niet aangetoond. NO_PROVEN_EDGE.

## Provenance

- ProphetX / PR Newswire, 2026-09-10: `ProphetX Partners with Agg Market to Bring Sports Prediction Markets to Solana`.
- Secundaire technische cross-check: NextPredict, 2026-09-10, beschrijving van SPL-tokenization/backing flow; nog niet als autoritatieve protocolsemantiek behandelen.
