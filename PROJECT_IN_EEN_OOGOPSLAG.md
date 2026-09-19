# Project in één oogopslag

Dit document is expres simpel gehouden. Het is bedoeld om in een paar minuten te zien **wat het project doet, wat er nu gebeurt en wat nog niet bewezen is**.

## Doel

We bouwen een doorlopend onderzoeksysteem voor prediction markets.

Het systeem zoekt continu naar legale economische zwaktes, test ideeën zo goedkoop mogelijk, bewaart wat niet werkt en onderzoekt alleen sterke survivors verder.

Belangrijk: **winstgevendheid wordt nooit vooraf aangenomen.**

Huidige economische status: **NO_PROVEN_EDGE**.

## Hoe het werkt

```text
nieuwe markt / nieuws / rule change / opvallende flow
                    ↓
          idee of afwijking gevonden
                    ↓
        check: kennen we dit al?
                    ↓
         PRE-BUILD KILLER
                    ↓
 semantiek → economie → data → execution
                    ↓
       meestal: TESTED_NEGATIVE
                    ↓
       soms: serieuze survivor
                    ↓
 replay → validation → holdout → shadow
                    ↓
      pas daarna eventueel micro-live
```

## Wat continu wordt onderzocht

- verschillende prediction-marketvenues;
- contract- en payoutlogica;
- settlement, finality en oracle-mechanismen;
- fees, rewards, collateral en incentives;
- market making en adverse selection;
- behavioral flow zoals FOMO, herding en framing;
- cross-venue verschillen;
- unusual rule/lifecycle edge cases;
- nieuws, papers, GitHub, documentatiewijzigingen en incidenten;
- publieke lessen uit misbruik- en integriteitscases;
- dark-marketmechanismen alleen als intelligencebron, niet als execution-lane.

## De belangrijkste onderdelen

### Knowledge Base

`bas1231/onderzoek` is het geheugen van het project.

Hier bewaren we:

- hypotheses;
- bewezen feiten;
- experimenten;
- mislukte ideeën;
- mechanismen;
- relevante bronnen;
- regels voor agents.

Een negatief resultaat wordt nooit verwijderd. Zo onderzoeken we dezelfde doodlopende route niet steeds opnieuw.

### News & Weak Signals

Een agent scant ieder uur naar relevante veranderingen, bijvoorbeeld:

- nieuwe venues/producten;
- rule changes;
- API/changelog-updates;
- fees/rewards;
- settlement- of oraclewijzigingen;
- incidenten;
- nieuwe papers/datasets;
- wat publieke traders zeggen dat werkt of juist faalt.

Hij zoekt bewust ook buiten prediction markets naar mechanismen die overdraagbaar kunnen zijn.

### Pre-Build Killer

Een idee krijgt niet automatisch code.

Eerst moet het goedkope checks overleven:

1. Is het nieuw of al eerder getest?
2. Klopt de contract-/settlementlogica?
3. Is er überhaupt genoeg theoretische marge?
4. Is er goedkoop empirisch bewijs?
5. Overleeft het echte bid/ask, fees, depth en fills?

Alleen daarna kan iets `BUILD_APPROVED` krijgen.

### Execution Lab

Hier worden strategieën getest alsof ze werkelijk uitgevoerd moesten worden.

Dus niet alleen midpoint of mooie backtestprijzen, maar onder meer:

- echte bid/ask;
- orderbook depth;
- fees;
- slippage;
- partial fills;
- queue/fill-risico;
- latency;
- collateral/capital lock;
- settlement/finality.

### Live Momentum Dashboard

Het dashboard moet later onder andere tonen:

- snel stijgende activiteit;
- price explosions;
- flow explosions;
- depth collapse;
- behavioral candidates;
- informed-flow warnings;
- cross-venue afwijkingen;
- belangrijke news/weak signals.

Het dashboard gebruikt dezelfde lokale datastream als de research-engine en hoort dus geen onnodige extra API-polls te veroorzaken.

## Hoe we chaos voorkomen

Harde projectregels:

- maximaal **1 actieve build** tegelijk;
- maximaal **3 actieve diepe hypotheses** tegelijk;
- één centrale statuspagina;
- agents mogen ideeën voorstellen, maar niet zomaar nieuwe systemen bouwen;
- oude services/experimenten worden opgeruimd of gearchiveerd;
- geen nieuwe agent of module zonder duidelijk bestaansrecht;
- iedere milestone eindigt met cleanup;
- nieuwe interessante zijpaden gaan eerst naar backlog, niet direct naar code.

## Wat jij normaal hoeft te doen

Zo weinig mogelijk.

In de gewenste eindsituatie hoef jij vooral:

- belangrijke survivors te beoordelen;
- eventueel een build/micro-live stap goed te keuren;
- lokale credentials of echte geldacties zelf te beheren;
- af en toe een lokale foutmelding door te geven als dat nodig is.

Het project hoort niet afhankelijk te zijn van uren terminalwerk van jou.

## Harde grens

**ILLEGAL = HARD STOP.**

Legaal grijs, vreemd of onbedoeld economisch gedrag mag agressief worden onderzocht.

Geen fraude, marktmanipulatie, spoofing, wash trading, collusie, credentialmisbruik, sabotage, ongeautoriseerde toegang of operationeel misbruik van software/securitykwetsbaarheden.

## Wanneer noemen we iets echt succesvol?

Niet bij:

- een interessant idee;
- een mooie grafiek;
- een positieve backtest;
- één winstgevende trade.

Wel pas wanneer een methode standhoudt in:

```text
replay
→ validation
→ untouched holdout
→ prospective shadow
→ eventueel micro-live
→ herhaalde echte resultaten na kosten
```

Tot die tijd blijft de status:

**NO_PROVEN_EDGE**.

## Korte huidige stand

- Knowledge base: actief
- Red-team methodiek: vastgelegd
- News & Weak Signals-agent: actief
- Negative evidence: actief
- Pre-Build Killer: ontworpen, nog te bouwen als centrale V0
- Mechanism/venue graph: ontworpen
- Live Momentum Dashboard: ontworpen
- Execution Lab: ontworpen
- Live trader: bewust nog niet bouwen
- Proven edge: geen

## Wat nu als eerste gebouwd moet worden

De kleine V0:

1. Candidate Registry
2. Knowledge/Negative Memory-koppeling
3. Pre-Build Killer
4. centrale projectstatus
5. klein dashboard

Daarna pas meer agents, zware replay of live execution.
