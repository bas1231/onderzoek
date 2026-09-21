# Hourly finding — Kalshi incentive programs — 2026-09-21 08:00 CEST

Status: RESEARCH_POSITIVE_MECHANISM / NO_PROVEN_EDGE

## Nieuwe primaire evidence

Kalshi's actuele publieke documentatie beschrijft twee economische overlays die nog niet in de canonieke Git-memory stonden:

1. Volume Incentive Program: actieve rewardperioden per markt, proportionele verdeling naar eligible volume, maximaal $0.005 reward per contract, normale event-contracten alleen tussen $0.03 en $0.97, en markt-/zijde-specifieke eligibility. De helpdocumentatie noemt als programma-einde 1 september 2027 en sluit onder meer internationale gebruikers uit.
2. Liquidity Incentive Program: rewards voor resting orders, gescoord via een willekeurige snapshot eenmaal per seconde. Target Size is >100 en <20.000 contracten; Reference Price wordt per snapshot bepaald op het eerste prijsniveau waar cumulatieve resting size 1/5 van Target Size bereikt; score is size x afstandsmultiplier en daarna relatief genormaliseerd. Alleen snapshots met voldoende two-sided liquidity tellen; payout wordt evenredig verlaagd voor excluded snapshots. Programma-einde volgens actuele helpdocumentatie: 1 januari 2027.
3. Kalshi vermeldt dat incentive-programdefinities (markt, type, start/einde, pool en liquidityparameters) via de publieke Trade API beschikbaar zijn.

Primaire bronnen, geraadpleegd 2026-09-21:
- https://help.kalshi.com/en/articles/13823850-what-is-the-kalshi-volume-incentive-program
- https://help.kalshi.com/en/articles/13823851-liquidity-incentive-program
- https://help.kalshi.com/en/articles/16076644-liquidity-and-volume-incentive-programs-where-to-find-them
- https://help.kalshi.com/en/articles/13823805-fees

## Specialist-routing

### scout
Nieuwe product/economic-overlay gevonden: rewardprogramma's zijn publiek machineleesbaar en kunnen dus prospectief als marktstate worden gearchiveerd.

### microstructure
Liquidity rewards veranderen de economics van resting quotes, maar een reward-indicator of headline pool is geen execution edge. De uiteindelijke payout hangt af van concurrenten, random snapshots, two-sided Target Size, afstand tot Reference Price, excluded snapshots, fills/adverse selection en eventuele makerfees. Reward-estimates zijn expliciet niet finaal.

### behavioral
Geen nieuwe behavioral edge bewezen. Incentives kunnen participantgedrag en gemeten volume/liquidity endogeen veranderen; historische volume- of maker-signalen rond incentivized markets moeten daarom incentive-regime als covariaat/provenance dragen.

### informed_flow
Geen informed-flow edge bewezen. Incentivegedreven volume kan order-flow-signatures vervuilen; hoge activiteit is niet automatisch information-driven flow.

### algebra
Reward cashflow is een externe, state- en participant-afhankelijke overlay en geen statische contract-payout identity. Zij mag alleen als aparte cashflowterm worden toegevoegd wanneer eligibility en prospectieve payoutregels bewezen zijn.

### settlement
Reward-finality staat los van contract settlement. Actieve/live estimates zijn niet finaal; paid credit is de finale reward-evidence.

### weather_twc
Geen nieuwe weather/TWC/KWI-uitkomst. Wel geldt: als KXTEMP-markten incentives hebben, moeten die point-in-time naast L2/fees worden vastgelegd voordat execution economics wordt beoordeeld.

## Pre-Build Killer

GEEN BUILD WARRANT. Er is geen actuele markt geselecteerd met aangetoonde netto positieve reward-adjusted execution. Voor de gebruiker is bovendien de officiële Volume Incentive Program-eligibility een directe blocker zolang de account als internationaal/niet-US wordt behandeld. De liquidity-documentatie sluit eveneens internationale gebruikers uit.

## Chief Falsifier

Een vermeende incentive-edge faalt totdat minimaal is bewezen:
- actuele market/program eligibility en user eligibility;
- contemporaneous pool, Target Size, Discount Factor en periode;
- echte maker/taker fee provenance;
- fill/adverse-selection/inventory risk;
- aandeel in kwalificerende liquidity/volume versus concurrenten;
- excluded-snapshot fraction;
- reward finality versus slechts UI-estimate;
- netto cashflow na fees, spread/slippage, fills en capital lock.

Geen Independent Reproducer: nog geen positieve economische instance.

## Besluit

Dit is duurzame nieuwe mechanism/economic-context, geen bewezen strategie. Voeg incentives voortaan als point-in-time execution-provenance toe aan relevante Kalshi studies. Geen nieuwe actieve candidate zonder concrete netto-positive instance.

Economische status: NO_PROVEN_EDGE.
