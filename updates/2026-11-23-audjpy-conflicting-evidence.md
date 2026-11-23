# AUDJPY: the one lead has CONFLICTING evidence — do not treat it as a lead until reconciled

**Date:** 2026-11-23T08:50Z · **Author:** Kilo · Paper only.
Tool: `tools/audjpy_tradelevel_check.py` → `reports/audjpy_tradelevel_check.json`.

## Two sources, opposite signs
| source | population | n | mean/trade | median | wins | notes |
|---|---|---:|---:|---:|---|---|
| **audit3 symbol block** | aggregate | 34 | **+0.576%** | — | — | DSR 0.815, verdict WEAK |
| **riseoftheclaw signal_tracking** | trade-level | 24 | **−2.45%** | **−5.21%** | **2 / 24** | sign-test p ≈ 3.6e-05; one implausible **+142%** value |

Additional trade-level detail: mean excluding the top-3 = **−13.6%**; 10% trimmed mean = **−9.9%**; the single +142% value
is **implausible for AUDJPY** in one trade (likely a data error or a different instrument) yet it dominates the mean.

## What this means
The **trade-level** sample is a **decisively losing pattern** (2 wins of 24, median −5.2%, p≈0). It does **not**
corroborate the audit3 aggregate of +0.576%. Either the two datasets are different trades, or the aggregate is driven by
an outlier / a different computation. **Until someone reconciles them on the same population, AUDJPY is NOT a reliable
lead.**

## Why I am stating this rather than picking a side
I have now reversed on AUDJPY twice this session (lead → "lost" → "lead again"). The honest resolution is not a third
flip; it is to **name the conflict and stop**: two internal sources disagree in *sign* on the single symbol the whole
programme was closest to. That is a **data-integrity problem**, and it should be resolved before any recommendation rests
on AUDJPY.

## Status change
- AUDJPY moves from **"the one genuine lead"** → **"unreconciled; not actionable."**
- The top-line is unaffected and remains the firmest result: **0 investable.**
- Action for the owner: reconcile the two AUDJPY populations (which trades are in each? is +142% real?), then re-run DSR.

*Paper only. Not investment advice.*
