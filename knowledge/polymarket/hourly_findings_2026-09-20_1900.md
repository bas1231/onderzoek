# Polymarket hourly findings — 2026-09-20 19:00 CEST

Status: **FACT_VERIFIED / STRUCTURAL_CANDIDATE / NO_PROVEN_EDGE**

## PM-NR-V2-CONVERT-001 — huidige V2 collateral adapter exposeert NO→complement-YES conversie

### Nieuwe evidence

De actuele publieke `Polymarket/ctf-exchange-v2` broncode voor `NegRiskCtfCollateralAdapter.sol` bevat een externe `convertPositions(bytes32 _marketId, uint256 _indexSet, uint256 _amount)` functie. De code:

- haalt voor iedere bit die in `_indexSet` staat de corresponderende NO-posities bij de caller op;
- roept daarna de legacy `NegRiskAdapter.convertPositions(...)` aan;
- berekent `amountOut = amount - amount * feeBips / 10_000`;
- stuurt vervolgens YES-posities terug voor de vragen waarvan de bit **niet** in `_indexSet` staat;
- wrapt eventueel ontvangen USDC.e terug naar de huidige collateral token voor de caller.

Daarmee is de eerdere `VERSION_EXECUTION_UNPROVEN`-vraag gedeeltelijk opgelost: de huidige V2 collateral-adapterlaag bevat expliciet een user-callable brug naar de legacy NegRisk-conversie. De huidige transformatiegraaf bevat dus minimaal de primitive:

`NO(S) -> YES(Q \ S)` minus de markt-specifieke `feeBips`, voor de door de adapter/markt toegestane indexsets.

Dezelfde broncode laat ook zien dat V2 split/merge/redeem voor NegRisk via de legacy NegRisk adapter blijft lopen. De V2 exchange-repository documenteert daarnaast een gedeployde `NegRiskCtfCollateralAdapter` en `NegRiskCtfExchangeV2` op Polygon.

### Betekenis voor Market Algebra

Een payout-equivalentie alleen is nog onvoldoende. Voor NegRisk kan de theorem-prover nu echter een concrete protocol-edge toevoegen met parameters:

- marketId;
- questionCount;
- indexSet/subset;
- input NO inventory;
- output complement-YES inventory;
- `feeBips`;
- collateral/wrapping state;
- approvals;
- gas;
- executable L2 cost/value van input en output.

De economische test wordt daarmee expliciet:

`executable_value(output YES complement after fee) - executable_cost(input NO subset) - gas - slippage - legging/inventory risk`.

Geen midpoint, last trade of theoretische $1 identity mag hiervoor als execution proof worden gebruikt.

### Pre-Build Killer

**Geen strategy-build warrant in deze run.** De protocolprimitive is bewezen in huidige broncode, maar er is geen gesynchroniseerde actuele L2/depth, geen gemeten `feeBips` voor een concrete actieve marketId, geen gas-/approval-/inventoryberekening en geen onafhankelijke reproductie van een economisch positieve instance.

### Chief Falsifier

1. **Semantiek/version:** current V2 source bevestigt de callable adapterroute; dit deel overleeft. De exacte deployed bytecode/address-versie is in deze run niet onafhankelijk on-chain geverifieerd.
2. **Data:** geen concrete actuele marketId + questionCount + feeBips + simultane books; market edge blijft onbewezen.
3. **Execution:** conversie vereist inputinventory/approvals en heeft expliciete fee; gas, depth, partial execution en waardering van meerdere outputlegs ontbreken. Execution edge blijft onbewezen.

### Status

- protocol primitive: `FACT_VERIFIED` uit huidige officiële broncode;
- algebra lane: `STRUCTURAL_CANDIDATE`;
- market edge: `UNPROVEN`;
- execution edge: `UNPROVEN`;
- economische eindstatus: `NO_PROVEN_EDGE`.

### Provenance

Primaire bron: `Polymarket/ctf-exchange-v2`, `src/adapters/NegRiskCtfCollateralAdapter.sol`, geraadpleegd 2026-09-20. Relevante regels/functionele elementen: immutable legacy adapter, `convertPositions`, `getQuestionCount`, `getFeeBips`, NO-input selectie, complement-YES-outputselectie en fee-adjusted `amountOut`.

Secundaire bevestiging uitsluitend als discovery/context: publieke V2 indexer/substreams-projecten herkennen de V2 NegRisk collateral adapter en `PositionsConverted` lifecycle; deze zijn niet gebruikt als primaire semantische autoriteit.
