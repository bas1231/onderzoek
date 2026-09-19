# Kalshi MLB strikeout ladder scan — 2026-09-19

Status: **TESTED_NEGATIVE for simple headline mispricing / NO_PROVEN_EDGE**

## Hypothesis

Current Kalshi MLB pitcher strikeout ladders may contain materially underpriced high-probability thresholds when compared with sportsbook prop markets and independent projection models.

## Three-angle test

### 1. Semantic / rules

Pitcher strikeout contracts are not always plain binary pre-start bets. Current rule text contains a scratch/non-start branch that can settle to a fair-market-price style outcome if the named pitcher does not start. Relief appearances are not treated as qualifying starter performance. Therefore any pre-start probability comparison must first confirm starter status and exact series rules.

### 2. Independent probability / market references

A spot-check of current headline K lines for pitchers including Jackson Jobe, Noah Gasser, Eury Perez, Casey Mize, Matthew Boyd, Nick Lodolo, Cam Schlittler and others found Kalshi visible prices broadly aligned with contemporaneous sportsbook strikeout markets after removing vig. No large robust gap survived a direct comparison on the main lines.

Independent projection sources also disagreed materially for some pitchers. Jackson Jobe was the clearest warning: public projections spanned roughly the low-3s to about 6 strikeouts depending on model/lineup assumptions. Cam Schlittler was more stable around the high-5s/low-6s, but his 6+ market was already close to sportsbook fair value.

Interpretation: a model probability >=80% at an alternate threshold cannot be treated as signal edge when reputable models disagree this much or when the sportsbook market already embeds a similar probability.

### 3. Execution

No claim in this scan had contemporaneous authenticated/full-L2 Kalshi evidence, exact fee calculation, depth walk or partial-fill modelling. Web/UI values were candidate discovery only. Therefore even a small gross discrepancy would remain `UNPROVEN` economically.

## Decision

The simple strategy `find a high-probability pitcher K threshold whose visible Kalshi price looks too low` is **not supported by this spot-check**.

This does not close all MLB microstructure research. Potentially distinct future hypotheses include:
- shape inconsistency across a complete same-pitcher threshold ladder;
- stale ladder legs immediately after confirmed lineup/starter news;
- cross-threshold monotonicity violations with simultaneous executable L2;
- conditional miscalibration by pitch count, opponent K%, umpire/park/weather or manager hook tendencies.

Each of those requires a new pre-registered experiment and must not reuse this negative scan as positive evidence.

## Kill / reopen rule

Do not reopen the simple headline-line lane unless a fresh candidate has:
1. confirmed exact starter/settlement semantics;
2. at least two independent probability references supporting a material gap;
3. simultaneous executable Kalshi L2 with net edge after fees/depth/latency.

Economic status remains **NO_PROVEN_EDGE**.
