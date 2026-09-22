# ForecastEx block/RFQ access kill-check — 2026-09-22

Status: `WATCH / ACCESS_AND_EFFECTIVENESS_BLOCKED`
Economic conclusion: `NO_PROVEN_EDGE`

## Question

Do ForecastEx's newly certified Block Trading rules, proposed RFQ functionality and proposed Block Trading Fee Holiday create a practically accessible execution lane for this project (budget ~EUR 250), or is the lane blocked by participant class / membership / implementation status before any economic test is justified?

## Primary-source findings

### 1. Block Trading itself is certified

The CFTC DCM rule-filing register lists ForecastEx's filing **"Amending Rulebook to allow for Block Trading"** with receipt date 2026-09-02 and status **Certified** on 2026-09-17.

Source: CFTC DCM filings register, FEX entry.

This proves that a ForecastEx block-trading rule change exists. It does **not** prove that this project's retail/FCM-customer path can initiate or receive block trades, nor does it establish an executable minimum size.

### 2. RFQ is not yet established as available to this project

The CFTC register lists a separate FEX filing dated 2026-09-08 whose description says the rule change permits **Members** to use ForecastEx's Request for Quote (RFQ) system to create quote-request messages expressing interest in a Forecast Market. As checked on 2026-09-22, the register still shows **10 Day Review**.

This is important for two reasons:

- the public filing description scopes RFQ to **Members**;
- the filing is not yet shown as Certified in the CFTC register at this point-in-time.

Therefore RFQ must not be treated as a currently proven executable path for this project's customer account.

### 3. The Block Trading Fee Holiday is also not yet proven effective

The CFTC filing page for FEX filing 63737 describes an amendment adding a **Block Trading Fee Holiday** for Block Trades executed between **2026-09-22 and 2026-12-01**. However, as checked on 2026-09-22, the CFTC register still shows the filing status as **10 Day Review**.

Therefore the intended holiday period is not sufficient evidence that the fee holiday is currently effective. Current fee economics remain `UNKNOWN` until certification/effective status and the applicable clean fee schedule are captured.

### 4. Direct ForecastEx membership is economically incompatible with this project

ForecastEx's current public Membership page says Members are subject to a **minimum Clearing Fund deposit of $250,000**. The ForecastEx Rulebook also states that each Member's Clearing Fund contribution is subject to a minimum size of at least $250,000.

Given this project's approximately EUR 250 research/trading budget, direct ForecastEx Membership is not a viable access path.

This is an access/capital constraint, not a statement about general retail customer eligibility.

### 5. Ordinary customer access through an FCM does exist

ForecastEx Rule 304 states that a person who is not eligible to become a ForecastEx Member may enter Forecast Contracts by becoming a Customer of an FCM Member or Sponsored FCM. Rule 403 says customer Bids are submitted through the FCM/Sponsored FCM via an Authorized Trading User.

So the ordinary Forecast Contract path remains potentially accessible through an intermediary even though direct membership is not.

What is **not** yet established is whether that customer path can use the new Member-facing RFQ functionality or participate in block trades on customer instructions, and under what minimum size / broker policy / fee conditions.

## Fail-closed decision

Do **not** build a ForecastEx block/RFQ execution strategy from the rule-change headline.

Current gate state:

- Block Trading rule exists: `PASS`
- Direct Membership feasible for project budget: `FAIL`
- Ordinary FCM customer access to Forecast Contracts: `PASS`
- Customer access to RFQ: `UNKNOWN`
- Customer access to Block Trading: `UNKNOWN`
- Block minimum size: `UNKNOWN`
- RFQ minimum size / response semantics: `UNKNOWN`
- Block Trading Fee Holiday currently effective: `UNKNOWN / CFTC still 10 Day Review`
- Point-in-time executable block/RFQ quotes: `MISSING`
- Net executable edge: `NOT TESTABLE YET`

## Next decisive question

The cheapest decisive follow-up is **not** market scanning. It is to establish from a primary ForecastEx rule/notice, FCM documentation, or direct broker capability documentation:

1. whether an FCM Customer may originate/respond to an RFQ or block trade through its FCM;
2. the minimum block quantity / notional for Forecast Contracts;
3. the applicable current block/RFQ fees after the CFTC filing's actual effective/certified state;
4. whether block/RFQ execution is exposed through any customer-accessible electronic/API path or is operationally Member-only.

If the customer path is unavailable or the minimum size is materially above the project's budget, close this trigger as `ACCESS_BLOCKED` without spending model or engineering capacity on execution analysis.

No paid action, account opening, broker contact, trade, wallet action or live execution is authorized by this note.

Economic conclusion remains `NO_PROVEN_EDGE`.
