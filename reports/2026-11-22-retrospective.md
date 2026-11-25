# Retrospective: how this programme should have found the cost problem first

**Date:** 2026-11-22 · **Owner:** buffy · **Item:** H50

Not a summary of what was done — a list of what would have made the same work converge faster,
written while the mistakes are still legible.

## 1. Price the round trip before running the backtest

The programme ran a 40-cell sweep and then discovered that **fees are 94% of the funding carry's
round trip**, that equity breakout flips sign between 4 and 10 bp/side, and that the per-class
cost floor ranges from **18 bp (FUTURES, 1.8× the assumed cost)** to **614 bp (EQUITY, 30.7×)**.

Every one of those is computable *before* any signal is evaluated. A single table — "what round
trip does each class pay, and what gross edge would it need to clear cash" — would have ranked the
cells by *plausibility* instead of by observed performance, and the observed performance is exactly
what multiplicity punishes. Cost needs no multiplicity correction: it is the same number for every
cell in a class.

**Rule adopted:** a per-class cost floor is now the first artifact of any round, not the last.

## 2. Report the margin, not the verdict

`FAILS_MULTIPLICITY` at DSR 0.9469 read as "the evidence is negative". It was not: the cell held
0.95 up to **N=28** against 29 declared, and needed **77 more trading days**. A one-trial,
77-day margin is `NOT_PROVEN`, which is a different instruction to the reader than `FAIL`.

The cost of the wrong label is not cosmetic: the correct label changes whether an independent
replication is worth commissioning — and for H-201 it plainly is.

**Rule adopted:** no significance verdict ships without the flip point (the parameter value at
which it changes) beside it.

## 3. When a peer disputes a number, run *their* specification

The commodity conflict took several rounds because the two sides were running different strategies:
a single binary on the **basket index** (43% invested) versus per-member SMAs (86% invested). The
entire 575 bp disagreement lived in that one line. Once the peer published the weight function and
I ran **their** construction, the answer was immediate and negative on both — CI-LB
**−24.18 bp/month**, halves **[−20.28, +34.10]**.

**Rule adopted:** a dispute over a number is settled on the disputant's construction, never on a
re-description of one's own. And a peer's *self*-correction is still a claim: measure it.

## 4. Fix the harness before trusting the headline

Four defects were found in the momentum core (look-ahead, NaN→short, Sharpe ~1e16, daily vs
monthly series), a positive-subset median trap was checked for and cleared, and this round's own
new tools produced two bugs **on first execution**: a bisection hunting the wrong end of a
true-then-false predicate (printing a margin of −99,971 trials), and a bootstrap run on a shorter
window than the table it was checking (turning a +0.57 pp advantage into −1.91).

Both were caught by making the tool *refuse to publish* when its reproduction check failed. That
is the design pattern that paid: gates that abort, not warnings that scroll.

**Rule adopted:** every new measurement tool must reproduce a number that already exists before it
is allowed to produce a new one.

## 5. Distrust the one-regime result, including your own

HRP "beat" 60/40 on the full sample and **lost by 1.93 pp** on the window where both series exist.
Vol targeting improved drawdown on daily data (**−22.37 vs −31.42**) and **worsened** it monthly
(**−33.72 vs −28.45**). Carry crossings moved 136 → 111 → 71 → 32 days as one assumption changed.
Each of those would have shipped as a finding under a looser standard.

**Rule adopted:** a result that exists in one window, one frequency, or one regime is reported as
a *sensitivity*, never as a result.

## What would have been done differently, in one sentence

**Cost first, margins beside every verdict, and every claim checked on the window where both
series actually exist** — in that order, before any signal is evaluated.
