# Threshold ↔ Exact — execution-first CPI lane

Datum: 2026-09-19
Status: **STRUCTURAL_CANDIDATE / NO_PROVEN_EDGE**

## Kernidee

Voor een onderliggende waarde die op een vaste discretisatie wordt afgerekend, kan een exact-bucket uit twee aangrenzende thresholds worden opgebouwd.

Voor een één-decimaal gerapporteerde waarde `x` en bucket `k`:

`1{x = k} = 1{x > k-0.1} - 1{x > k}`

Daaruit volgt voor standaard YES/NO-contracten de drie-leg cashflow-identiteit:

`YES(x > k-0.1) + NO(x > k) + NO(x = k) = $2`

voor iedere toegestane settlementwaarde, **mits** threshold- en exact-series exact dezelfde bron, meetperiode, transformatie, rounding/discretisatie en exception branches gebruiken.

Dit is een payout-identiteit, geen kansmodel.

## Actuele candidate-generation observaties

### Core CPI YoY September 2026 — k = 2.4

Kalshi webweergave, gecrawld 2026-09-19:

- `KXCPICOREYOY-26SEP`: Above 2.3% — YES ask-weergave 84c
- `KXCPICOREYOY-26SEP`: Above 2.4% — NO ask-weergave 54c
- `KXECONSTATCORECPIYOY-26SEP`: Exactly 2.4% — NO ask-weergave 59c

Som zichtbare legs: `84 + 54 + 59 = 197c`.

Als de identiteit semantisch exact geldig is, is de settlement-floor $2.00 en is de **bruto zichtbare gap 3c**.

Bronnen:
- https://kalshi.com/markets/kxcpicoreyoy/core-inflation/kxcpicoreyoy-26sep
- https://kalshi.com/markets/kxeconstatcorecpiyoy/year-over-year-core-inflation/kxeconstatcorecpiyoy-26sep

### Headline CPI YoY September 2026 — k = 3.7

Kalshi webweergave, gecrawld 2026-09-19:

- `KXCPIYOY-26SEP`: Above 3.6% — YES 45c
- `KXCPIYOY-26SEP`: Above 3.7% — NO 83c
- `KXECONSTATCPIYOY-26SEP`: Exactly 3.7% — NO 70c

Som zichtbare legs: `45 + 83 + 70 = 198c`.

Bruto zichtbare gap bij bewezen identity: **2c**.

Bronnen:
- https://kalshi.com/markets/kx/test/kxcpiyoy-26sep
- https://kalshi.com/markets/kxeconstatcpiyoy/year-over-year-inflation/kxeconstatcpiyoy-26sep

## Zeer belangrijke execution-waarschuwing

Deze web/UI-prijzen zijn **geen execution proof**. Volgens bestaande repo-regel `KAL-UI-001` mogen UI/chance/search-snippets niet als contemporaneous executable L2 worden behandeld.

Voor promotie is nodig:

- simultane point-in-time orderbooks van alle drie legs;
- voldoende depth voor dezelfde target quantity;
- actuele series fee state / fee changes / eventuele waiver;
- exacte order timestamps en cross-leg skew;
- settlement/rules hashes voor beide series;
- partial-fill/legging model.

## Fee check

Kalshi publiceert een algemene takerfee van de vorm:

`round_up(M * 0.07 * C * P * (1-P))`

met series-specifieke uitzonderingen/multipliers. De API documentatie exposeert bovendien een publieke endpoint voor geplande series fee changes en marktvelden voor fee-waivers/overrides in relevante responses.

Onder de standaard takercoëfficiënt en 100 complete Core-CPI baskets bedragen de ruwe fees bij 84c/54c/59c ongeveer:

- 84c leg: ~$0.95 per 100
- 54c leg: ~$1.74 per 100
- 59c leg: ~$1.70 per 100
- totaal: ~$4.39 per 100 complete baskets = ~4.39c per basket

Dat is groter dan de 3c bruto gap. **De takerroute is dus niet positief onder deze standaard-feeaanname.**

Voor headline 45c/83c/70c komt de standaard takerfee eveneens boven de 2c bruto gap uit.

CPI-series kunnen volgens de actuele fee-schedule samenvattingen makerfees hebben; de exacte point-in-time multiplier moet vóór iedere executiontest uit primaire series-fee data worden gebonden.

Primaire fee/help/API bronnen:
- https://help.kalshi.com/en/articles/13823805-fees
- https://docs.kalshi.com/api-reference/exchange/get-series-fee-changes

## Makerroute: mogelijk interessant, maar niet automatisch veilig

Een passieve maker-entry heeft lagere expliciete fee-frictie dan taker-entry wanneer de betreffende series makerfees hanteert, en in sommige series kan makerfee nul zijn. Maar een makerbasket is niet automatisch een locked trade:

- een buy order op een bestaande ask is taker, niet maker;
- passieve bids moeten eerst gevuld worden;
- fills van de drie legs zijn niet atomisch aangetoond;
- één of twee fills zonder de rest creëren een ongedekte positie.

Daarom moet een makerstrategie een **state-by-state completion gate** gebruiken: na iedere partial fill moet de resterende hedge direct via actuele FOK/IOC-prijzen nog een conservatief positieve `net_locked_edge` hebben, anders mag de initiële makerquote niet geplaatst/promoveerd worden.

## Execution primitives die wél beschikbaar zijn

Kalshi FIX-documentatie ondersteunt per individuele order:

- Post Only;
- IOC;
- FOK;
- MaxExecutionCost.

Bron: https://docs.kalshi.com/fix/order-entry

Kalshi Order Groups limiteren het aantal gematchte contracten in een rolling 15-second window en annuleren groeporders wanneer de limiet wordt geraakt. Dit is een risk-control primitive, **geen gedocumenteerde atomische multi-market all-or-none basket**.

Bron: https://docs.kalshi.com/api-reference/order-groups/create-order-group

## Drie-invalshoekencheck

### 1. Formeel / payoff

Status: **PASS CONDITIONALLY**

De algebra is exact onder de aanname dat de threshold- en exact-contracten dezelfde gediscretiseerde settlementvariabele gebruiken:

`A = 1{x > k-0.1}`
`B = 1{x > k}`
`E = 1{x = k}`

Bij één-decimaal discrete `x` geldt `E=A-B`; dus:

`A + (1-B) + (1-E) = 2`.

Open blocker: de concrete huidige rules_primary/rules_secondary van beide series moeten side-by-side worden vastgelegd en gehasht; titel/source-overeenkomst is onvoldoende.

### 2. Onafhankelijke/historische semantiekcheck

Status: **PARTIAL SUPPORT, NOT PROOF**

De resolved August 2026 exact Core-CPI-YoY event toont `Exactly 2.4% = Yes`; de corresponderende thresholdfamilie is eveneens BLS Core-CPI-YoY. Dit ondersteunt dat de productfamilies bedoeld zijn als exact versus threshold representaties van dezelfde macrovariabele, maar één resolved voorbeeld vervangt geen concrete rule-equivalence proof voor September.

Bronnen:
- https://kalshi.com/markets/kxeconstatcorecpiyoy/year-over-year-core-inflation/kxeconstatcorecpiyoy-26aug
- https://kalshi.com/markets/kxcpicoreyoy/core-inflation/kxcpicoreyoy-26aug

### 3. Live/economische execution

Status: **FAIL / NOT PROVEN**

- UI-weergaven tonen bruto +2c en +3c candidates.
- Geen simultane L2/depth capture in deze researchpass.
- Standaard takerfees overschrijden de bruto gaps.
- Makerroute kan de fee hurdle verlagen maar introduceert fill/legging risk; cross-market atomicity is niet bewezen.

Daarom blijft economische status `NO_PROVEN_EDGE`.

## Nieuwe onderzoekshypothese

De interessante lane is niet specifiek CPI 2.4 of 3.7, maar een **universele threshold↔exact cashflow scanner**:

1. canonicaliseer settlementsemantiek;
2. bind aangrenzende thresholds aan exacte buckets;
3. bereken de gegarandeerde floor algebraïsch;
4. lees simultane L2 en actuele fee-state;
5. test taker-completion direct;
6. test maker-entry alleen wanneer iedere partial-fill state nog veilig fee-net voltooid kan worden;
7. log candidate lifetime en executable quantity.

De Strix/i9 is goed geschikt om veel ladders en exact-series lokaal te canonicaliseren en te vergelijken; de strategie mag niet afhankelijk zijn van colocatie of microseconde-races.

## Falsificatie / killcriteria

- Kill ieder paar met andere source, measurement window, comparator, rounding/discretisatie, revision policy of exception branch.
- Kill candidate als contemporaneous L2 de bruto cross niet bevestigt.
- Kill takerroute als fees + slippage + buffer >= gross floor gap.
- Kill makerroute als een mogelijke partial-fill state niet veilig met actuele FOK/IOC kan worden voltooid zonder negatieve worst-case edge.
- Deprioritize lane als prospectieve census geen herhaalde fee-net positive opportunities vindt met lifetime passend bij retail latency.
