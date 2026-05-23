---
name: hypothesis-registry-explained
description: Use when someone asks what the hypothesis registry is, why it exists, what pre-registration / M-107 means, what a harness or harness run is, or what "eff" / "admissible" mean. Conceptual explainer, not a workflow.
---

# hypothesis-registry-explained — the why behind the registry + harness

This skill explains the *concepts*. To actually register or test a hypothesis,
use the companion skill `hypothesis-registry`.

## What the hypothesis registry is

`reports/hypothesis_registry.json` — a single JSON file that records every
trading-strategy idea ("hypothesis") the system has ever tried, each with a
fixed ID (`H-001`, `H-002`, …), its exact definition, and its verdict.

It is a **lab notebook with a lock**: an idea is written down, with its test
design fully specified, *before* anyone runs the backtest. After the test, the
verdict is appended and never edited away.

## Why it exists — the problem it solves

**Data-dredging / p-hacking.** If you backtest 100 random strategies, ~5 will
look profitable at the 95% level by pure chance. If you are allowed to tweak the
signal, the threshold, the date window, or the symbol list *after seeing
results*, you will always eventually find a curve that looks like edge — and it
will be noise that collapses the moment real money touches it.

Pre-registration (rule **M-107**) kills this. You commit — publicly, with a
git timestamp — to the **exact** signal definition and the **exact** pass/fail
criteria *before* touching data. Then you run it once. You cannot retroactively
move the goalposts, because the goalposts are already committed to `main`.

This is the same discipline clinical trials use (pre-registered endpoints) and
the same idea as the "deflated Sharpe ratio" in quant finance — correcting for
how many things you tried.

**Why we have it here specifically:** this system accumulated 8,000+ picks from
dozens of emitters and a "rehab/mutate the losers" culture. That is a
data-dredging machine. Without pre-registration, every inflated dashboard tile
and every lucky cohort looked like an edge. The registry is the firewall: an
idea only counts if it was pre-registered and *then* cleared the harness.

## What a "harness" is

The **harness** is `tools/edge_stability_harness.py` — the single, unmodifiable
falsification test that decides whether a hypothesis has real edge or is noise.
Calling it the "harness" because it straps a strategy in and stress-tests it.

A **"harness run"** = feeding a built strategy's resolved picks into
`is_admissible()` and getting a verdict. Mechanically:

1. Take the strategy's resolved picks — each is WON or LOST and carries a
   **signal-magnitude** value (how strong the signal was for that pick).
2. Split the picks into rolling **14-day walk-forward windows** (out-of-sample
   slices through time).
3. In each window compute **`eff`** = effect size =
   `(mean signal-magnitude of WINNERS − mean of LOSERS) / pooled standard deviation`.
   Plain English: *does a stronger signal actually go with a winning trade?*
4. A window counts as "strong" if `|eff| ≥ 0.30` and it holds ≥80 picks.
5. The strategy is **ADMISSIBLE** only if **≥3 of 5 windows are strong AND they
   all have the same sign** — i.e. the edge points the same direction in every
   period, not flipping with the market regime.
6. Plus a **post-cost gate**: net edge must keep ≥60% of gross after a realistic
   ~30 bps round-trip cost. A 2 bps "edge" that costs 30 bps to capture is not edge.

## Why the same-sign rule is the heart of it

Almost every failed hypothesis dies here. A signal can *look* predictive
in-sample, but if its `eff` is +0.5 in bull months and −0.5 in bear months, it
has **no stable edge** — it is just tracking the regime, and you cannot know
the regime in advance. The same-sign-across-windows requirement is the test for
"real, generalizable edge" vs "regime noise." 11 of 11 pre-registered
hypotheses have failed, and the dominant cause is sign instability.

## The vocabulary

| Term | Meaning |
|------|---------|
| **M-107** | The rule: pre-register before backtesting. |
| **eff** | Effect size — does signal strength separate winners from losers, in std-dev units. |
| **window** | A 14-day walk-forward (out-of-sample) slice of the picks. |
| **admissible** | Passed the harness — real-edge candidate. |
| **REJECTED** | Harness scored it and it failed (a genuine kill). |
| **UNTESTED** | Too few picks/windows to even score — a data-gap, NOT a pass. |
| **cost-survival** | % of gross edge left after trading costs. |
| **canonical ledger** | `pf_registry.json` — policy-clean, deduped. The verdict-grade data. Dashboard tiles are NOT canonical (they inflate). |

## The honest current state

11 hypotheses pre-registered and harness-tested → 11 killed, 0 admissible
(`reports/EDGE_HUNT_EXHAUSTED_2026-05-18.md`). The registry's value is not that
it found edge — it is that it has *honestly proven the absence of edge* and
prevented 11 noise-strategies from being sized with real money. A registry full
of honest kills is the system working correctly.

## Reference
- Registry: `reports/hypothesis_registry.json`
- Harness: `tools/edge_stability_harness.py`
- Workflow skill: `hypothesis-registry`
- Kill log + macro verdict: `reports/EDGE_HUNT_EXHAUSTED_2026-05-18.md`, `reports/MACRO_WHY_NO_EDGE_2026-05-18.md`
