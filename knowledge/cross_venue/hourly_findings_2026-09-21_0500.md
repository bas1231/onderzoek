# Hourly finding — World / Chainlink settlement architecture — 2026-09-21 05:00 CEST

Status: **RESEARCH_POSITIVE (mechanism discovery) / NO_PROVEN_EDGE**

## Nieuwe evidence

Een nieuwe venue/mechanism-sweep vond World, een Solana prediction-marketvenue die in september 2026 als standalone platform is geopend. Primaire Chainlink-bronnen bevestigen dat World Chainlink als oracle-infrastructuur gebruikt: CRE voor snelle/deterministische outcome resolution en Data Streams voor high-performance crypto prediction markets. Chainlink noemt voor World uitbreiding naar macro/markets, major sports en elections.

Primaire bron:
- https://chain.link/blog/chainlink-defi-announcements (2026-08-25; World-sectie)
- https://chain.link/use-cases/prediction-markets (actuele productdocumentatie)

Een onafhankelijke technische reverse-engineering door Chainstack Labs beschrijft een andere belangrijke laag: World gebruikt volgens hun on-chain reconstructie Token-2022 YES/NO-pairs met CASH collateral, dealer/RFQ-pricing via DFlow en een operator-controlled on-chain resolution instruction. Hun actuele onderzoek meldt tevens een open market-catalog endpoint en een World proxy voor maker quotes zonder API-key, plus per-fill variabele fees/spread. Dit is secundaire/code-derived evidence en moet vóór formele venue-integratie onafhankelijk worden gereproduceerd.

Secundaire/codebron:
- https://github.com/chainstacklabs/world-xyz-research
- https://github.com/chainstacklabs/world-xyz-research/blob/main/docs/reference.md

## Conceptuele routing

- **scout:** nieuwe venue/mechanism family; niet aanwezig in huidige Git-memory search.
- **settlement:** belangrijke architectuurvraag: Chainlink kan off-chain outcome computation leveren terwijl de on-chain program state mogelijk door een operator key wordt gezet. Oracle provenance, operator authority en protocol finality moeten dus apart worden bewezen.
- **algebra:** complete-set mint/burn (`1 CASH -> YES + NO`) is structureel interessant maar op zichzelf slechts payout identity, geen wealth creation.
- **microstructure:** RFQ/dealer quotes zijn geen CLOB. Een execution-test moet daadwerkelijke contemporaneous buy/sell quotes, quote lifetime, fees/spread, size en fillability gebruiken; catalog bid/ask of UI-prijs is onvoldoende.
- **behavioral:** geen nieuwe evidence.
- **informed_flow:** geen nieuwe evidence.
- **weather_twc:** geen nieuwe evidence.

## Pre-Build Killer

Geen build warrant. Er is nog geen aangetoonde economische headroom. De complete-set identity reduceert zonder prijsfrictie tot collateral accounting. RFQ fees/spread kunnen theoretische cross-venue of complementverschillen gemakkelijk opslokken. De execution surface verschilt fundamenteel van een open CLOB.

## Chief Falsifier

Harde blockers vóór economische promotie:
1. onafhankelijk reproduceren welke World catalog/quote endpoints werkelijk publiek en point-in-time bruikbaar zijn;
2. actuele fee/spread-formule en quote-size/lifetime bewijzen;
3. on-chain authority en resolution provenance direct uit program/account data verifiëren;
4. settlement source/rules per market vastleggen; generieke Chainlink-marketing is geen market-specifiek settlementbewijs;
5. alleen simultane executable RFQ versus andere venue/portfolio vergelijken, inclusief Solana/network fees, slippage, capital lock en partial execution.

De apparent spanning tussen generieke Chainlink-claims over cryptografisch verifieerbare/on-chain outcome proofs en Chainstack's World-specifieke observatie van een operator-written outcome is **geen contradiction resolved**. Zij kunnen verschillende systeemlagen beschrijven. Tot directe reproductie blijft dit een settlement provenance gap.

## Independent Reproducer

Niet geactiveerd: nog geen positieve economische instance. Onafhankelijke technische reproductie van de World resolution/quote surface is wel de goedkoopste volgende falsificatietest als deze lane prioriteit krijgt.

## Economische conclusie

Signal edge: niet bewezen.
Market edge: niet bewezen.
Execution edge: niet bewezen.

**NO_PROVEN_EDGE**.
