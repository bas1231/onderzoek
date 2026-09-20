# Polymarket hourly findings — 2026-09-20 20:00 CEST

Status: **FACT_VERIFIED / MODEL_CORRECTION / STRUCTURAL_CANDIDATE / NO_PROVEN_EDGE**

## PM-NR-CONVERT-CASHFLOW-002 — NegRisk conversion output bevat collateral én complement-YES

### Nieuwe evidence / correctie

De 19:00 finding modelleerde de huidige V2 `convertPositions` primitive te smal als `NO(S) -> YES(Q\\S) minus fee`. De officiële NegRisk-adapterdocumentatie specificeert de onderliggende cashflow preciezer: wanneer een markt `n` vragen heeft en `_amount` van `m` NO-posities wordt geconverteerd, ontvangt de gebruiker `_amount * (m-1)` collateral plus `_amount` van iedere complementaire YES-positie, vóór toepassing van een eventuele conversion fee. De huidige V2 `NegRiskCtfCollateralAdapter` bevestigt dat eventueel uit de legacy adapter ontvangen USDC.e na conversie wordt gewrapt en aan de caller wordt teruggegeven, terwijl complement-YES tokens fee-adjusted worden uitgekeerd.

Daarom moet de Market Algebra primitive niet alleen token-output maar de **volledige cashflowvector** modelleren:

`m × NO(amount) -> collateral component + complement-YES component - conversion fee`

waarbij exacte fee-toerekening en wrapped-collateral accounting uit de actuele contractstate/source moeten worden afgeleid voordat een economische vergelijking wordt gemaakt.

Dit is materieel: een scanner die alleen de complement-YES-output waardeert kan de economische waarde van de conversie verkeerd berekenen en zowel false negatives als foutieve headroomberekeningen produceren.

### Semantische caveat

De officiële adapterdocumentatie vermeldt tevens dat de equivalentie veronderstelt dat exact één vraag in de NegRisk-markt uiteindelijk TRUE wordt. Als alle vragen FALSE eindigen, is de geconverteerde positie minder waard dan de oorspronkelijke NO-set; meer dan één TRUE is protocolmatig niet toegestaan. Dit maakt de settlement-state invariant onderdeel van het proof-object, niet slechts metadata.

### Pre-Build Killer

Geen strategy-build warrant. De cashflowcorrectie verandert het formele model, maar er is nog steeds geen concrete actuele actieve marketId met point-in-time input/output books, on-chain `questionCount`, `feeBips`, gas, approvals en inventory. De finding rechtvaardigt een modelcorrectie vóór een toekomstige census, niet live execution.

### Chief Falsifier

1. **Semantiek:** officiële legacy-adapterdocumentatie + huidige V2 wrappercode zijn consistent dat conversion collateral kan opleveren naast complement-YES; de 19:00 shorthand was incompleet.
2. **Settlement:** payout-equivalentie vereist de exact-one-TRUE invariant; all-FALSE is expliciet een failure state voor volledige equivalence.
3. **Execution:** geen simultane L2/depth of concrete fee/gas state; market edge en execution edge blijven onbewezen.

### Additional discovery

Een publieke third-party Substreams-indexer beschrijft gratis on-chain eventtypen waarmee later `MarketPrepared`, `QuestionPrepared`, `PositionsConverted`, fills en resolution-events kunnen worden gereconstrueerd. Dit is alleen een tooling lead; geen primaire semantische evidence en nog geen gratis end-to-end datafeed bewezen. Een andere V2 indexer vereist een HyperSync token en is daarom niet automatisch toegelaten als `free_public` dependency zonder aparte verificatie.

### Status

- 19:00 primitive: **CORRECTED / INCOMPLETE CASHFLOW MODEL**;
- full cashflow requirement: **FACT_VERIFIED**;
- exact-one-TRUE settlement invariant: **FACT_VERIFIED**;
- structural algebra lane: **KEEP RESEARCHING**;
- market edge: **UNPROVEN**;
- execution edge: **UNPROVEN**;
- economische eindstatus: **NO_PROVEN_EDGE**.

### Provenance

Primaire bronnen, geraadpleegd 2026-09-20:
- `Polymarket/neg-risk-ctf-adapter`, `docs/NegRiskAdapter.md` (`convertPositions` semantics and exact-one-TRUE caveat);
- `Polymarket/ctf-exchange-v2`, `src/adapters/NegRiskCtfCollateralAdapter.sol` (current V2 wrapper: questionCount, feeBips, complement YES output and wrapping of received USDC.e).

Secundaire tooling lead: `bluehoodie/substreams-polymarket`; niet gebruikt als semantische autoriteit.