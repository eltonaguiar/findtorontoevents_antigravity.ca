# GARCH asymmetric-band sensitivity test — result (2026-06-20)
**Author:** claude-opus · honest first-touch (SL-wins-ties), crypto_ohlcv 1h, NO winsorize · σ from `garch_volatility.get_garch_forecast` (trailing-only, no look-ahead) · **Companion:** `reports/FRM_CFA_CONCEPTS_AUDIT_2026-06-20.md`

## Setup
200 CRYPTO closed picks (honest cohort, ≤15/symbol, inside the crypto_ohlcv replayable window). For each: replay stored fixed TP/SL vs **asymmetric GARCH bands** (TP = entry ± 3.0σ, SL = entry ∓ 1.5σ; σ = 1h GARCH vol forecast on trailing 250 closes). Net @16bp. CI-LB = cluster bootstrap (symbol-day). NOTE: broad CRYPTO honest cohort, **not** the exact rsi5070_us slice.

## Result
| Variant | trueWR | net PF | CI-LB | mean ret | hits |
|---|---|---|---|---|---|
| Baseline (stored fixed bands) | 45.5% | 1.183 | 0.834 | +0.296% | SL 109 / TP 91 |
| GARCH asym (TP 3.0σ / SL 1.5σ) | 46.0% | **1.423** | **0.970** | +0.380% | SL 108 / TP 92 |

Asymmetric vol bands lifted net PF +0.24 (1.18→1.42) and CI-LB +0.14 (0.83→0.97) — a real, measured improvement, **better than the FRM/CFA audit predicted** (it called vol bands a near-relabel for this lead).

## Honest caveats (why this is a LEAD, not a FIX)
1. **Still sub-bar.** CI-LB 0.970 < 1.15 even after the improvement. Band geometry alone does NOT manufacture a promotable edge; n remains the binding constraint (n_eff 85, just over the 80 floor). Consistent with the coverage finding (`MEASUREMENT_COVERAGE_BOTTLENECK_2026-06-20.md`).
2. **Partly mechanical.** A ~2:1 reward:risk band is profitable at any WR>33%; this cohort is ~46% WR, so a wider-TP/tighter-SL band helps almost by construction. The near-identical hit counts (SL 109→108, TP 91→92) despite a wider 3σ TP are mildly suspicious and need verification (does WR hold at the wider TP?).
3. **Single parameterization, no OOS band-validation.** 3.0σ/1.5σ was pre-specified (not swept), which limits but does not eliminate curve-fit risk. The session's recurring lesson: positive-looking results dissolve under scrutiny (H-126 clustering, daily-resolution inflation).

## Recommended follow-up (rigorous, before any trust)
- Re-run on the EXACT rsi5070_us cohort (not the broad CRYPTO set).
- Estimate band params (k_tp, k_sl) on an IS window, apply to OOS — confirm the lift survives out-of-sample (no in-sample band tuning).
- Time-split the cohort; confirm the improvement holds in both halves (guard against sample-specific noise).
- Pair with the OHLCV backfill (more n → tighter CI): asymmetric vol bands + more honest n could be a *contributing* path to clearing the bar — but neither alone suffices.

## Bottom line
A genuine, modest lever (not the zero the audit expected) — but **not a fix**: it leaves the cohort sub-bar and carries mechanical + parameterization caveats. Worth a rigorous OOS band-param study on the rsi5070 lead specifically, ranked BELOW the coverage backfill (which addresses the binding n constraint).
