# Current /audit Strategies — Baseline to Outperform

**Date:** 2026-04-19
**Source:** `https://findtorontoevents.ca/audit/data/dashboard_data.json` (realized data)
**Filter:** n ≥ 30 resolved trades. **57 strategies qualified.**

## Top 15 by total realized PnL

| # | System / Strategy | n | WR | avg PnL | total PnL |
|---|---|---|---|---|---|
| 1 | claude_gainer_st / st_fear_greed_contrarian | 718 | 57.1% | +0.83% | **+593.4%** |
| 2 | mercury2 / ensemble | 231 | 40.7% | +0.64% | +148.7% |
| 3 | aggregated_picks / Extreme Fear Contrarian Buy | 71 | **67.6%** | +1.77% | +125.4% |
| 4 | luxalgo_filters / luxalgo_confluence | 803 | 43.0% | +0.14% | +115.6% |
| 5 | aggregated_picks / Multi-Timeframe Trend Alignment | 39 | **89.7%** | **+2.96%** | +115.5% |
| 6 | claude_gainer_st / st_obv_support_divergence | 241 | 52.7% | +0.37% | +90.2% |
| 7 | signal_validation / MeanReversionBB | 100 | 58.0% | +0.83% | +82.6% |
| 8 | claude_gainer / claude_gainer_4h | 32 | 56.2% | +2.51% | +80.2% |
| 9 | ml_bg_system_f / extreme_fear | 153 | 49.7% | +0.49% | +75.0% |
| 10 | rapid_fire / rsi_bounce | 41 | 48.8% | +1.80% | +73.8% |
| 11 | baby_strats_forward / vwap_deviation_reversion_doge_v1 | 51 | 11.8% | +1.18% | +60.0% |
| 12 | stocks_competition / Bollinger MR | 74 | 51.4% | +0.75% | +55.8% |
| 13 | dna_winner_picks / claude_ml_moderate_mut | 71 | 53.5% | +0.63% | +44.7% |
| 14 | ml_crypto_pred / ml_crypto_pred | 32 | 28.1% | +1.39% | +44.6% |
| 15 | stocks_competition / Breakout Momentum | 66 | 51.5% | +0.57% | +37.7% |

## Bar any new strategy must clear to "outperform current"

| Metric | Threshold | Rationale |
|---|---|---|
| WR | ≥ 55% | Top-10 median sits here |
| avg PnL | ≥ +0.60% | Post-cost edge threshold |
| n | ≥ 100 | Wilson LB precision |
| Wilson 95% LB on WR | ≥ 52% | Bonferroni correction on k tested |
| Sharpe rolling 30d | ≥ 1.0 | Strategy Lifecycle Policy v1.1 |
| Max DD vs avg_loss ratio | ≤ 3× | Fat-tail safety |
| Regime coverage | ≥ 4/5 F&G buckets | Per peer-review amendment |

## Data caveat (critical)

**`st_fear_greed_contrarian` conflict**: dashboard shows 57.1% WR / +593% total (n=718). PR #257 reports 28.3% WR / −456% total (n=3525). **Two different numbers for the same strategy name.** Root cause: `strategy_performance.json` writer regression (PR #258 P0+) drops entries between cycles, so different snapshots see different populations. Treat baseline as "what dashboard aggregates currently" — not ground truth.

## Current candidates being tested

| Candidate | Source | S1 stats | Meets bar? |
|---|---|---|---|
| **Keltner Fresh-Break** | Kimi (branch `feature/baby-strategies-mfi-cmo-keltner-aroon`) | n=154, WR 57.1%, PF 1.30, Sharpe 1.63 | **Yes** (matches baseline #7) |
| MFI Extreme Reversion | Kimi | n=110, WR 53.6%, PF 1.28, Sharpe 1.45 | Close — WR 1.4pp below bar |
| CMO Extreme Reversion | Kimi | n=90, WR 52.2%, Sharpe 1.47 | n too small |
| Aroon Oscillator | Kimi | n=529, WR 50.1%, Sharpe 1.78 | WR below bar |
| Altcoin basis arb (B1) | pending S1 agent | in-flight | TBD |
| VVIX/VIX mean reversion (C3) | pending S1 agent | in-flight | TBD |

## Today's FAILs (archived)

- CR-1 Funding Reversion: n=4 in 3yr. Untestable.
- EQ-1 PEAD mid-cap: Sharpe 0.04, WR 36.6%.

**Today's hit rate: ~15% on hand-picked "strongest" candidates.** This is the expected yield from honest validation.

## Honest verdict

One candidate **ties** baseline #7 (Kimi's Keltner Fresh-Break WR 57.1%). No candidate has yet **beaten** the top-3. The realistic path to outperforming current is:

1. Fix `strategy_performance.json` writer (PR #257/#258 P0+)
2. Merge Kimi's validated 4 strategies into paper-test pipeline
3. Let S1 results from B1/C3 land; keep only survivors
4. Accept that ≥90 days of forward-paper testing is mandatory before any "outperform" claim is real
