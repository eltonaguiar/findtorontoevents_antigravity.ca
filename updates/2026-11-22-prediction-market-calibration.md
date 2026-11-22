# Prediction market calibration — Polymarket (2026-11-22)

Reproducer: `python3 tools/prediction_market_calibration.py --max 400 --lead-days 7`
Artifacts: `reports/prediction_market_calibration/calibration.json`
Closes todo **41**.

Method note that matters: prices are taken **7 days before resolution**, not at
resolution. The final price is ~0 or ~1 by construction, so using it would be
circular. This is the price you could actually have transacted at.

---

## Headline

| | |
|---|---|
| resolved binary markets collected | 400 |
| with usable price history | **362** (38 dropped for missing/short history) |
| base rate (YES frequency) | 37.02% |
| **Brier score (market)** | **0.1176** |
| Brier (0.5 climatology) | 0.2500 |
| Brier (base-rate climatology) | 0.2331 |
| **Brier skill vs base rate** | **+0.4956** |

**Polymarket prices carry real information.** A 50% reduction in Brier error
against the best naive forecast is a large, unambiguous skill number. Whatever
follows, it does not overturn that.

## Calibration curve

| bucket | n | mean price | YES rate | gap | 95% CI | reading |
|---|---:|---:|---:|---:|---|---|
| 0.00–0.10 | 84 | 0.036 | 0.048 | +0.012 | [0.019, 0.116] | calibrated |
| 0.10–0.20 | 42 | 0.142 | 0.119 | −0.023 | [0.052, 0.250] | calibrated |
| **0.20–0.30** | 41 | 0.247 | **0.024** | **−0.223** | [0.004, 0.126] | **price too high** |
| 0.30–0.40 | 19 | 0.349 | 0.474 | +0.125 | [0.273, 0.683] | calibrated |
| **0.40–0.50** | 43 | 0.450 | **0.279** | **−0.171** | [0.167, 0.427] | **price too high** |
| 0.50–0.60 | 42 | 0.525 | 0.476 | −0.049 | [0.334, 0.623] | calibrated |
| 0.60–0.70 | 12 | 0.650 | 0.667 | +0.017 | [0.391, 0.862] | calibrated (n<20) |
| 0.70–0.80 | 13 | 0.750 | 0.846 | +0.096 | [0.578, 0.957] | calibrated (n<20) |
| 0.80–0.90 | 19 | 0.853 | 0.947 | +0.095 | [0.754, 0.991] | calibrated (n<20) |
| 0.90–1.00 | 47 | 0.963 | 0.979 | +0.015 | [0.889, 0.996] | calibrated |

Two buckets have outcome CIs that exclude their mean price, both in the same
direction: **contracts priced 0.20–0.50 delivered YES far less often than priced.**
The extreme tail buckets (0.00–0.10 and 0.90–1.00, n=84 and n=47 — the two
largest) are almost perfectly calibrated.

## Why I am not calling this an edge

1. **Multiple testing.** 10 buckets were examined; 2 came back "significant";
   the expected count by chance at α=0.05 is **0.5**. Under a binomial with
   p=0.05, n=10, P(X ≥ 2) ≈ **0.086** — not significant.
2. **Small buckets.** The two flagged cells have n=41 and n=43. The 0.20–0.30
   cell's CI lower bound (0.004) clears the bucket edge (0.20) by a hair.
3. **Direction is the familiar one but in an unfamiliar place.** The
   favourite-longshot bias is usually a tail effect. Here the *tails are
   calibrated* and the deviation sits in the middle. That is unusual enough to
   need replication before belief.
4. **The gap is gross.** Polymarket charges no trading fee on most markets, but
   the **spread is UNMEASURED** — measuring it needs a per-market book at
   decision time. A 0.17–0.22 probability gap sounds large, but the honest
   position is gate 1 of `docs/PROMOTION_GATE_2026-11-22.md`: **unmeasured cost
   cannot support a promotion, only a rejection.**

## Labels

| item | label | basis |
|---|---|---|
| Polymarket calibration (aggregate) | **ESTABLISHED** | Brier skill +0.4956 vs base rate, n=362 |
| "Prices too high at 0.20–0.50" | **CANDIDATE / SHADOW** | 2/10 buckets, binomial p≈0.086, spread UNMEASURED |
| Tradeable prediction-market edge | **UNMEASURED** | gross gap only; no measured spread |

This is the second clean "the market is efficient" result in the programme (after
the ETF tactical engine failing to beat static 60/40). It is worth stating plainly
because it is the base rate for every future claim: **most of the time, the price
is right.**

## What would promote the mid-range deviation

Pre-register it — bucket 0.20–0.50, YES-side short, fixed 7-day lead, n≥200 out
of sample — **before** looking at any more data, plus a measured spread. Absent
both, it stays in SHADOW.
