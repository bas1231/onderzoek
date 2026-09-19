# Execution-first cashflow discovery

Datum: 2026-09-19
Status: **METHODOLOGY — NO_PROVEN_EDGE**

## Kernverschuiving

Zoek niet primair naar prijsafwijkingen, rare midpoints of theoretische mispricings. Zoek primair naar **cashflows/payoffs die op het beslismoment werkelijk kunnen worden vastgelegd en die na executionkosten een positieve ondergrens hebben**.

De centrale vraag is dus niet:

> "Waar wijkt de prijs af?"

maar:

> "Welke positie of portfolio kan ik nu daadwerkelijk construeren, wat betaalt die in iedere toegestane settlementstate uit, en blijft de slechtste netto cashflow positief na alle kosten en uitvoeringsrisico's?"

Een prijsafwijking is alleen discovery. Een kans wordt pas economisch interessant wanneer de executable cashflow zelf positief is.

## Prioriteitsvolgorde

Voor structurele/algebraïsche kansen geldt voortaan bij voorkeur:

`payoff/settlement semantics -> constructeerbare cashflow -> simultaneous executable bid/ask + L2 depth -> fees -> slippage -> partial-fill/legging risk -> latency/finality -> netto worst-case payout -> economic materiality -> validation`

Niet:

`midpoint anomaly -> veronderstelde edge -> execution achteraf`

## Minimale execution-aware berekening

Voor iedere kandidaat moet waar relevant worden vastgelegd:

- exacte settlement/payofffunctie per leg;
- bewezen relatie tussen de legs;
- koop-/verkooprichting per leg;
- gelijktijdige executable bid/ask, niet alleen midpoint/UI chance/last trade;
- beschikbare quantity/depth op de benodigde prijsniveaus;
- fees per leg;
- slippagebuffer;
- partial-fill/legging scenario;
- relevante latency/finality/collateral-risico's;
- gegarandeerde of conservatieve netto payout-floor;
- maximale executable quantity waarop die floor nog geldt.

Een nuttige kernmaat is:

`net_locked_edge = worst_case_settlement_cashflow - executable_cost - fees - slippage_buffer - execution_risk_buffer`

Voor een hedge/short-constructie wordt dezelfde logica met de juiste cashflowtekens toegepast.

Alleen wanneer `net_locked_edge > 0` onder conservatieve, point-in-time aannames is een kandidaat execution-positive genoeg om naar de volgende gate te gaan.

## Economische materialiteitsgate

Een positieve locked edge is **noodzakelijk maar niet voldoende**. Een technisch correcte arbitrage kan praktisch waardeloos zijn als slechts enkele contracts beschikbaar zijn of het kapitaal jarenlang vaststaat.

Bereken daarom aanvullend minimaal:

- `executable_capacity_contracts`;
- `absolute_locked_profit_usd = net_locked_edge_per_contract * executable_capacity_contracts`;
- `capital_locked_usd`;
- `days_to_expected_cash_release`;
- `return_on_locked_capital`;
- `return_per_capital_day` en waar zinvol annualized return;
- verwachte herhaalbaarheid/frequentie van dezelfde opportunity class.

Prioriteer geen candidate uitsluitend omdat `net_locked_edge > 0`. Een 1c edge met vijf contracts en jaren capital lock is research-technisch positief maar economisch laag-prioriteit.

Voor de lokale Strix/Starlink-doelstelling krijgen kansen hogere prioriteit wanneer zij tegelijk:

1. een formeel/verifieerbaar positieve floor hebben;
2. voldoende depth/capacity hebben voor materiële absolute dollars;
3. relatief kort capital lock hebben of vroeg collateral/cash vrijgeven zonder de payoffgarantie te verbreken;
4. lang genoeg executable blijven voor retail-netwerklatency;
5. prospectief herhaalbaar zijn.

## Bevinding uit handmatige Kalshi-tests — 2026-09-19

Tweede onderzoeksronde over Moment-SOS, Möbius, Walsh/Fourier, Hodge, Optimal Transport, MaxEnt/Ising, absorbed-martingale en Hawkes liet zien:

- algebraïsche/statistische methoden vinden relatief gemakkelijk prijsverschillen, midpoint-curl en synthetische/directe afwijkingen;
- deze verschillen verdwenen in de bekeken voorbeelden meestal zodra echte bid/ask, fees, spread, slippage of fill-risico werd meegenomen;
- een eerder waargenomen bruto CPI-cashflowkandidaat van circa `198c -> 200c` was daarom geen bewezen execution-edge; de quotes veranderden en de bruto marge was onvoldoende om meerdere takerlegs en fees overtuigend te overleven;
- de bottleneck is dus niet alleen het vinden van afwijkingen, maar vooral het vinden van een **uitvoerbare payoffconstructie waarvan de netto cashflow na alle fricties positief blijft**;
- fee-free exhaustive partitions bevestigen bovendien dat zelfs een echte below-par basket economisch onaantrekkelijk kan zijn door geringe capacity en lange settlementtijd; materialiteit en capital efficiency moeten daarom expliciet naast `net_locked_edge` worden gemeten.

Status van deze bevinding: `RESEARCH_POSITIVE` voor de methodologische richting, maar overall economische status blijft `NO_PROVEN_EDGE`.

## Discovery-prioriteit

Geef meer prioriteit aan kansen met één of meer van deze eigenschappen:

1. deterministische of formeel begrensde payout;
2. meerdere productpaden naar dezelfde settlementcashflow;
3. payoff dominance / locked lower bound;
4. voldoende dikke L2-depth om alle legs werkelijk te vullen;
5. marge die ruim groter is dan fees + spread + redelijke executionbuffer;
6. opportunity lifetime die past bij retail-infrastructuur;
7. weinig of beheersbaar legging/partial-fill-risico;
8. voldoende absolute profit bij de werkelijk executable capacity;
9. redelijke capital efficiency / settlementhorizon.

Geef lagere prioriteit aan:

- midpoint-only afwijkingen;
- verschillen kleiner dan de plausibele totale executionkosten;
- opportunities die alleen bestaan als alle legs exact tegelijk tegen theoretische prijzen vullen;
- races die uitsluitend met colocatie, gespecialiseerde low-latency networking of HFT-infrastructuur realistisch zijn;
- signalen zonder duidelijk pad naar een verhandelbare netto cashflow;
- formeel positieve maar economisch triviale kansen met zeer lage capacity of extreem lange capital lock.

## Relatie tot bestaande methoden

Möbius, Walsh/Fourier, Hodge, SOS, Optimal Transport en vergelijkbare technieken blijven nuttig, maar hun rol is vooral **candidate generation en formele payoff-analyse**. Zij mogen een anomalie niet automatisch als edge promoveren.

De gewenste architectuur wordt daarom conceptueel:

`candidate discovery -> payout theorem/identity -> executable cashflow construction -> L2/fees/fill verification -> conservative net edge -> materiality/capital-efficiency gate -> replay/holdout -> prospective shadow -> micro-live`

MaxEnt/Ising, martingale- en Hawkes-methoden kunnen daarnaast kandidaten rangschikken of adverse-selection/flowrisico signaleren, maar vervangen geen execution proof.

## Bewijsstandaard

Een agent mag pas spreken over een execution-positive candidate wanneer point-in-time evidence de volledige benodigde constructie ondersteunt. Ontbrekende simultane depth, onbekende fees, onzekere settlementsemantiek of niet-bewezen legging maken de status `UNKNOWN`, `STRUCTURAL_CANDIDATE` of `NO_PROVEN_EDGE`, niet `PROVEN_EDGE`.

Een execution-positive candidate wordt bovendien niet automatisch een economisch relevante opportunity. Daarvoor moet ook de materialiteitsgate standhouden: voldoende absolute locked profit, acceptabele capital efficiency en realistische herhaalbaarheid voor de beschikbare infrastructuur.
