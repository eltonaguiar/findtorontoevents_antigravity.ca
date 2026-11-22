# H-151 — net share issuance: the pre-registered test, refuted

**Verdict: NOT_PROVEN → REFUTED.** The frozen long-short spread is *negative*. The
signal does not merely fail to clear its gates; it points the wrong way.

- Run: 2026-11-22 · `tools/h151_net_issuance.py` · artifact `reports/h151_net_issuance_2026-11-22.json`
- Registry: `reports/hypothesis_registry.json`, H-151, `PRE_REGISTERED` → `REFUTED`
- Harness: `tools/edge_stability_harness.py`, imported unmodified (self-check: EFF_MIN 0.3,
  MIN_WINDOW_N 80, MIN_STABLE_WINDOWS 3 — all match the published values)

## What was frozen before the run

Registered 2026-11-22 with an empty `result` field: signal `NIS = ln(shares_t /
shares_{t-4q})` from `dei:EntityCommonStockSharesOutstanding`, usable only from
filed date + 1 trading session; quintiles, bottom long / top short, equal weight,
one-month hold, next-open entry, 10 bp per side; gates at 100 names per leg, 36
months, FF4 alpha t ≥ 2, appraisal ratio ≥ 0.5, cost survival ≥ 0.60.

Nothing in the spec moved after the numbers appeared. The one convention that had
to be chosen up front is the score sign: each record carries `gpa_score = -z(NIS)`
because the harness asks whether *higher* scores win more often and the hypothesis
says higher issuance *loses*. `nis_z` and `nis_raw` keep the unflipped signal beside it.

## Result

| Measure | Value |
|---|---|
| Names with share facts and prices | 568 |
| Records / formations | 29109 / 131 |
| Split-suspect name-quarters dropped | 970 |
| Name-quarters with no 12-month lookback | 19695 |
| Median names per leg | **43** (gate: 100) |
| Long-short spread, net | **-0.2054 %/month** |
| Same at 2x cost | -0.2054 %/month |
| Harness | REJECTED — 131 windows, 15 strong, sign *mixed* |
| Cost survival | 0.817 |
| FF4 alpha | -0.3567 %/month, **t = -0.63**, R² 0.204 |
| Appraisal ratio (FF4) | **-0.199** |
| IR of raw long-short | -0.104 |

Gates failed: `harness_admissible_positive`, `min_names_per_leg_100`, `factor_alpha_t_ge_2`, `appraisal_ge_0_5`, `raw_spread_positive`.

## Why this is a refutation and not a weak result

The registry lists three refutation conditions. The first is *"raw bottom-minus-top
spread ≤ 0 net of costs"* and it fires: the repurchaser leg lost
0.2054 %/month relative to the issuer leg. The FF4 intercept
is negative as well (-0.3567 %/month), so this is not a factor tilt
masquerading as a signal — the premium is absent before any adjustment and worse after.

The honest reading: **in this sample, firms that shrank their share count
underperformed firms that issued.** That is the opposite of the Baker-Wurgler
timing story and the opposite of what Pontiff & Woodgate (2008) document.

## What it does not say

Three limits, each of which would matter if someone tried to promote this either way:

1. **The legs are thin.** Median 43 names per leg against a
   registered minimum of 100. The point estimate is noisy; its *sign* is not the
   ambiguous part, but the magnitude should not be quoted as a premium.
2. **The sample is not a random sample of US equities.** It is the 756-CIK cache built
   for H-149/H-150, drawn for a mid-cap study. Selection into that cache correlates with
   having usable quarterly facts, which is not the same population as "US common stock".
3. **The spread is cost-insensitive by construction.** Both legs pay the same round
   trip, so doubling slippage cancels in the difference — the 2× figure is identical to
   the base case. Reported rather than hidden, but it means this test cannot be rescued
   or killed by the cost assumption.

The delisting gap noted in every equity test here (18 tickers with no price history at
all, all warrants or dead shells) biases results *upward*, so it cannot explain a
negative spread.

## Consequence

H-151 was one of the two ideas harvested from the local fleet in
`reports/2026-11-22-fleet-ideation-sweep.md`. It is now closed. The ETF creation/
redemption variant (proposal ET-1) is untouched by this: it measures arbitrage flow
on a basket, not managerial timing on an issuer, and it needs a different data field.
