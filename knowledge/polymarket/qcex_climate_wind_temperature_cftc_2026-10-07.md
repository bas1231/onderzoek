# QCEX / Polymarket US — climate contracts certified 2026-10-07

Status: **PRIMARY_RULE_EVIDENCE / NO_PROVEN_EDGE**. Discovered in Research-OS 2026-10-08 11:05 CEST.
Venue: QCX LLC d/b/a Polymarket US (QCEX). Do **not** conflate with international Polymarket contract semantics or access.

## Primary certification evidence
- Global Temperature Contracts (GTC) filing 65008: https://www.cftc.gov/IndustryOversight/IndustryFilings/TradingOrganizationProducts/65008
- Temperature class (GTCD) filing 65009: https://www.cftc.gov/IndustryOversight/IndustryFilings/TradingOrganizationProducts/65009
- GTC contract specification: https://www.cftc.gov/filings/ptc/ptc10072632238.pdf
- Wind Speed Contracts (WINDC) filing 65011: https://www.cftc.gov/IndustryOversight/IndustryFilings/TradingOrganizationProducts/65011
- Wind class (WINDCD) filing 65012: https://www.cftc.gov/IndustryOversight/IndustryFilings/TradingOrganizationProducts/65012
- WINDC contract specification: https://www.cftc.gov/filings/ptc/ptc10072632259.pdf

The 40.2(d) class certifications say intended listings are **no earlier than 2026-10-09**. Certified is not equivalent to listed, accessible or executable.

## Temperature: source and semantics
- Exchange is Source Agency. Source hierarchy: NOAA Aviation Weather Center routine METAR first; NCEI fallback under defined missing-routine-observation conditions; Weather Underground secondary under specified no-data circumstances.
- Routine METAR includes COR observations; SPECI does **not** count for temperature.
- Use T-group tenths °C when reported, otherwise main METAR temperature whole °C. Corrected same-time observations and receipt ordering can affect value.
- Local standard time defines day boundaries (special intraday convention); precision, conversions, source error and no-data/last-fair-price contingencies are explicit.
- NCEI and Weather Underground values do not override sufficient qualifying METAR observations merely because their values differ.

## Wind: source and semantics
- Exchange is Source Agency. Primary NOAA Aviation Weather Center METAR **and SPECI**. US-city NWS Daily Climate Report secondary only under specified conditions.
- Wind threshold concerns qualifying gusts `G` and `PK WND`, not sustained wind. Valid observation without gust can imply zero; missing wind group is a different case.
- Example contract: Amsterdam / Schiphol station EHAM, peak wind threshold 35 knots on 2027-03-03; example is not proof that this specific market is currently listed.
- `PK WND` can be observed in a report published up to an hour after period end if the peak's own time lies in period. Local standard time, knots conversion, correction rules, no-data and last-fair-price cases matter.
- Contiguous/exhaustive wind ranges are stated as mutually exclusive in ordinary paths, subject to no-data exceptions; do not assume an unconditional portfolio floor across exceptional states.

## Mechanism assessment
**Observation:** different settlement inputs and exceptional states between QCEX GTC, QCEX WINDC, Kalshi TWC hourly, Kalshi NWS daily, and Kalshi KWI.

**Inference:** matching city/date/threshold titles do not prove statewise payout equivalence across venues. Even within one venue, wind and temperature observation inclusion differs.

**Hypothesis (not edge):** after actual listing and confirmation of legitimate access, source-lock a concrete weather market and search for truly identical cross-venue payoff pairs; only then compare contemporaneous executable bid/ask, L2 depth, fees, collateral, fills and settlement.

**Red-team guardrails:** `CROSS_VENUE_SAME_WEATHER_TITLE_IS_NOT_IDENTICAL_PAYOFF`; `CERTIFIED_CONTRACT_IS_NOT_LISTED_OR_EXECUTABLE`; `METAR_SPECI_SOURCE_HIERARCHY_AND_EXCEPTION_STATES_BREAK_UNPROVEN_WEATHER_IDENTITIES`.

Existing negative evidence `hourly TWC versus daily NWS identity` is preserved, not reopened. No candidate promotion, kill or WATCH trigger authorized. Economic conclusion: **NO_PROVEN_EDGE**.

Related hourly report: `hourly-reports/hourly-20261008T1105+0200.md`.
