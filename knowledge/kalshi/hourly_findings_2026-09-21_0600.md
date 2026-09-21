# Kalshi hourly finding — 2026-09-21 06:00 CEST

Status: **RESEARCH_POSITIVE / MECHANISM_DISCOVERY — NO_PROVEN_EDGE**

## Nieuwe evidence
Op 18 september 2026 heeft KalshiEX bij de SEC een voorgestelde Rulebook v1.30 ingediend voor **Perpetual Security Futures Products (Perpetual SFPs)** op Amerikaanse aandelen/ETF's. Dit is een nieuwe product/mechanism-lane ten opzichte van de bestaande Git-memory, maar de producten zijn nog voorstel/pending en dus geen actuele execution-lane.

Primaire SEC-evidence uit Exhibit 4:
- Chapter 14 definieert perpetual SFPs zonder vooraf bepaalde expiratiedatum en met cash settlement.
- Contract Unit is 100 aandelen; fractionele contract-unit quantities kunnen volgens contractspecificaties worden toegestaan.
- Trading hours: zondag 18:00 ET t/m vrijdag 17:00 ET, met dagelijks onderhoud 17:00–18:00 ET, behoudens halts/discretionaire authority.
- Funding wordt per reguliere equity-session berekend uit 60-seconden Computation Intervals. Alleen intervallen met een berekenbare Premium tellen mee; als N=0 is funding nul.
- Funding Rate = mean premium minus een 0.002% deadband, daarna begrensd op ±2.00%. Periodic Transfers vinden plaats bij Daily Settlement Time.
- Mark Price heeft een tiered fallback: non-block-trade VWAP; anders 60 sampled midpoints indien two-sided en spread <=10%; anders prior mark plus verandering in Underlying Price Index; daarna index/Rule 7.1 fallback.
- Underlying Price Index is de consolidated-tape last sale; wanneer de cashmarkt gesloten is wordt de officiële closing price van de meest recente reguliere sessie gebruikt.
- Minimum customer margin is 15.50% van Current Market Value; de Exchange kan hoger eisen. Open posities worden dagelijks marked-to-market.
- Corporate actions kunnen adjustment, conversion of accelerated final cash settlement veroorzaken. Settlement/reference prices worden in beginsel als final behandeld ondanks latere revisies; completed settlement wordt niet heropend wegens een later gevonden fout, behoudens de in de regels genoemde pre-completion uitzonderingen/remedial mechanisms.

## Agent routing
### scout
Nieuwe Kalshi productfamilie/mechanisme gedetecteerd. Nog niet live/economisch bewezen.

### algebra
Interessante toekomstige carry/basis-structuur: perpetual SFP versus onderliggende equity/ETF en andere futures/perpetuals. Funding is echter path-dependent op Kalshi's eigen Mark Price en een session-average premium. Een spot/perp prijsverschil is daarom geen statische payout identity.

### microstructure
Belangrijke guardrail: Tier-2 mark price kan expliciet uit 60 sampled midpoints komen. Dat maakt UI/midpoint nog steeds geen executionbewijs, maar mark/funding modelling moet de officiële tier-selectie reconstrueren. De 10%-spreadfilter en Tier-3 fallback kunnen illiquide regimes materieel veranderen.

### settlement
Corporate actions, regulatory halts, discretionary safeguards, accelerated settlement en price-finality/revision semantics zijn first-class state. Point-in-time Exchange Notices en rule versioning zijn vereist voor elke toekomstige replay.

### behavioral / informed_flow / weather_twc
Geen directe nieuwe economische evidence uit deze filing.

## Pre-Build Killer
**KILL BUILD / KEEP AS WATCH-LANE.** Redenen:
1. product is nog proposed/pending, geen actuele executable market;
2. geen contemporaneous orderbook/fill/funding history;
3. geen aangetoonde netto carry/basis headroom na fees, margin, financing en execution;
4. mark/funding mechanics bevatten fallbacks en discretionaire states die simpele spot-perp algebra ongeldig maken.

## Chief Falsifier
Te falsificeren voordat dit ooit kandidaat wordt:
- regulatory approval/effective listing werkelijk bereikt;
- exacte contractspecificaties en participant/access route;
- actuele fee schedule en margin/collateral economics;
- reconstructeerbare mark-price tier en funding history;
- executable basis versus onderliggende cash/hedge na fees, financing, halts en corporate-action risk;
- geen edge claim uit indicative funding, midpoint of theoretical basis.

Independent Reproducer niet geactiveerd: geen positieve economische instance.

## Besluit
Nieuwe mechanism-evidence is duurzaam genoeg voor Git-memory, maar er is geen signal-, market- of execution-edge bewezen.

**NO_PROVEN_EDGE**.

## Provenance
Primaire bron: SEC, KalshiEX LLC Proposed Rule Change, Exhibit 4, Rulebook v1.30, gepubliceerd 18 september 2026 (`34-106422-ex4.pdf`).
Secundaire discoverybron: crypto.news, 20 september 2026; alleen gebruikt om de filing te vinden, niet als autoriteit voor de regels.
