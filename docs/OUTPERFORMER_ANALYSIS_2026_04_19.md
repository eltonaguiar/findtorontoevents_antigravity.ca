# Outperformer Analysis — 2026-04-19

**Analyst:** Claude Opus 4.7 (1M context)
**Question:** After the P0 track-writer fix (`305397e1a`), does any strategy — existing or newly proposed — outperform the current `/audit` baseline?
**Short answer:** **Almost no existing strategy passes the bar. One (`ml_enhanced_RENDERUSDT_1h_D_ensemble_stack`) marginally clears Wilson-95 LB > 50% at n=41–42, and none clear the Bonferroni-corrected bar. Among PR #260/#259/Kimi candidates, none yet pass the live bar; the closest candidate is `equity_low_vol_momentum_pullback` (n=341, avg_trade 0.64%, but WR 48.1% / W95 LB 0.428).**

All numbers below are computed live in `tmp_analysis/run_analysis.py` against current working-tree data (`alpha_engine/data/strategy_performance.json` @ 165 entries, `alpha_engine/data/closed_picks.json` @ 5264 rows, live `dashboard_data.json` from https://findtorontoevents.ca/audit/data/).

---

## 1. Data Pipeline State — P0 Fix Verdict

- **Initial read of `strategy_performance.json`:** 5 entries (matching the broken-writer symptom).
- **After waiting one cycle / reading the on-disk file again later in the same session:** **165 entries.** The P0 merge-write fix (commit `305397e1a`) IS working; the first read caught a stale snapshot between cycles. Full coverage is restored.
- **However:** of 165 tracked strategies, **only 6 have n ≥ 30** — the rest are ML-enhanced per-symbol-per-timeframe variants that each see 1–25 picks. This is a **fragmentation problem**, not a data-quality problem.
- `closed_picks.json` has **5264 rows**, **5090 carry a `strategy` field** (96.7% — much better than the earlier 14% figure; the ledger has largely been backfilled).

---

## 2. Top Existing Strategies (strategy_performance.json, n ≥ 30)

| Strategy | n | WR | Wilson-95 LB | Wilson-Bonf LB (k=6) | avg_pnl% | Composite |
|---|---:|---:|---:|---:|---:|---:|
| ml_enhanced_RENDERUSDT_1h_D_ensemble_stack | 41 | 0.659 | **0.506** | 0.463 | +0.0338 | +0.0171 |
| ml_enhanced_RENDERUSDT_4h_D_ensemble_stack | 31 | 0.613 | 0.438 | 0.383 | +0.0246 | +0.0108 |
| quan_engine_swing | 109 | 0.275 | 0.200 | 0.189 | -0.0001 | ~0 |
| macd_rsi_confluence | 30 | 0.400 | 0.246 | 0.205 | -0.0006 | ~0 |
| volume_spike_breakout | 40 | 0.125 | 0.055 | 0.039 | -0.0181 | -0.0010 |
| quan_engine_scalp | 4316 | 0.299 | 0.286 | 0.279 | -0.1673 | -0.048 |

**Passing Wilson-95 LB > 50% AND avg_pnl > 0:** 1 strategy — `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack`.
**Passing Wilson-Bonferroni LB > 50% (k=6):** 0 strategies.

Against the live ledger (`closed_picks.json`, n ≥ 15 relaxed) two more candidates appear that are not yet at the n≥30 bar but approach it:
- `ml_enhanced_INJUSDT_1d_B_lightgbm` — n=22, WR 95.5%, W95 LB **0.782**, avg +10.3% (PROMISING)
- `ml_enhanced_BNBUSDT_15m_B_lightgbm` — n=19, WR 89.5%, W95 LB **0.686**, avg +4.8%
- `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` — n=25, WR 96.0%, W95 LB **0.805**, avg +1.5%

These three "looks-too-good" candidates all sit in the 15 ≤ n < 30 window and likely reflect the RENDER pattern: concentrated wins on a single symbol in a benign regime window. They should be commissioned to S2 walk-forward before being counted as outperformers.

---

## 3. New-Candidate Strategies (PR #260 / #259 / Kimi)

### PR #260 `feat/baby-strategies-audit-baseline` — `baby_strategies/new_asset_class_backtest_results.json` (yfinance backtest, NOT live pool)

Pooled across symbols per strategy:

| Strategy | n | WR | W95 LB | avg_trade% | Composite | Pass live bar (WR≥55%, avg≥0.6%)? |
|---|---:|---:|---:|---:|---:|---|
| crypto_bb_squeeze_breakout_momentum | 21 | 0.476 | 0.283 | **3.134** | 0.888 | WR fails; avg strong |
| crypto_liquidity_trap_reversion | 78 | 0.526 | 0.416 | 0.726 | 0.302 | WR close; W95 fails |
| equity_low_vol_momentum_pullback | 341 | 0.481 | 0.428 | 0.637 | 0.273 | Closest to bar overall |
| equity_atr_gap_reclaim | 68 | 0.529 | 0.412 | 0.607 | 0.250 | Marginal |
| commodity_mom12_1_trend_dip | 350 | 0.451 | 0.400 | 0.586 | 0.235 | WR fails |
| commodity_breakout_failure_reversal | 102 | 0.490 | 0.395 | 0.434 | 0.172 | WR fails |
| equity_52w_high_pullback_momentum | 377 | 0.454 | 0.404 | 0.366 | 0.148 | avg light |
| commodity_vol_compression_trend_pullback | 83 | 0.470 | 0.366 | 0.289 | 0.106 | WR fails |
| crypto_realized_skew_contrarian | 58 | 0.500 | 0.375 | 0.239 | 0.090 | WR OK; avg light |
| forex_trend_breakout_atr_confirm | 66 | 0.470 | 0.354 | 0.128 | 0.045 | Both fail |
| forex_connors_rsi2_regime | 772 | 0.452 | 0.417 | -0.009 | ~0 | Fails (avg<0) |
| forex_range_reset_reversion | 19 | 0.316 | 0.154 | -0.170 | -0.03 | Fails |

**Outperform-note from PR #260 author:** 10 strategies pass "validated pool baseline" but **none match the stretch smart-gate counterfactual (60% WR, +0.59% mean).** My numbers corroborate: no PR #260 strategy meets WR≥55% AND avg≥0.6% AND W95 LB > 50% simultaneously. This is a **yfinance-universe backtest**, not live-pool validation — treat as screening only.

### PR #259 `ide-agent/add-strategies-2026-04-19` ("Quant Signal Engine Framework V2")
- This PR is the framework scaffold, not the previously-expected `donchian_adx_trend_breakout`. No backtest JSON artifacts shipped for a standalone Donchian+ADX strategy on this branch. (`feature/baby-donchian-mega-promoted` local branch exists but has no meta.json for donchian_adx.) **Defer until a meta.json lands.**

### Kimi branch `feature/baby-strategies-mfi-cmo-keltner-aroon`

| Strategy | total_trades | WR | W95 LB | Sharpe | PF | Status |
|---|---:|---:|---:|---:|---:|---|
| aroon_oscillator_reversal | 529 | 0.501 | 0.458 | 1.80 | 1.36 | `backtest_failed` per meta (flag) |
| cmo_extreme_reversion | 90 | 0.522 | 0.418 | 1.47 | 1.28 | `ready_for_forward_test` |
| keltner_fresh_break_reversion | 154 | 0.571 | 0.491 | 1.63 | 1.30 | **Best Kimi candidate** |
| mfi_extreme_reversion | 110 | 0.536 | 0.443 | 1.45 | 1.28 | `ready_for_forward_test` |

`keltner_fresh_break_reversion` is the single best new candidate by live-bar yardstick: WR 57.1% (borderline), W95 LB 0.491 (just below 50%), Sharpe 1.63, PF 1.30, n=154 across 29 symbols. **Right on the bar — good paper-flag candidate.**

---

## 4. `st_fear_greed_contrarian` reconciliation

Live dashboard carries TWO entries under this name:
- `systems[0].strategies[9]`: wins=1, losses=3, **WR 25%, n=4** (clean-metrics tier)
- `systems[16].strategies[0]`: wins=289, losses=556, **WR 34.2%, n=845** (raw aggregate)

**Neither matches the "WR 57.1% n=718" figure** quoted in the task. The PR #257 figure of **WR 28.3% n=3525** is directionally closer to the raw 34.2%/n=845 (sample-size mismatch remains — likely PR #257 pulled all historical picks including force-closed-toxic). The dashboard value is more recent and still negative. **The 57.1% figure appears to be stale or computed against a hand-picked sub-window; it should not be used.**

---

## 5. Verdict Per Category

- **Existing strategies:** Only `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` (n=41, W95 LB 0.506) passes the live bar — and only by 0.6 percentage points on the Wilson LB. Not Bonferroni-robust. `quan_engine_scalp` at n=4316 with WR 29.9% is the overwhelming mass of the book and is a net loser (-0.167% avg). **"No broad outperformer on live data."**
- **PR #260 candidates:** None pass the live bar. Closest is `equity_low_vol_momentum_pullback` (n=341, W95 LB 0.428, avg +0.64%) — falls ~7 pp short on WR. `crypto_bb_squeeze_breakout_momentum` has an appealing composite (avg 3.1%) but n=21 and WR 47.6% make it unreliable.
- **Kimi candidates:** `keltner_fresh_break_reversion` is the single real contender (WR 57.1%, n=154, Sharpe 1.63) and sits right at the 50% Wilson LB boundary.
- **Donchian+ADX (PR #259/feature/baby-donchian-mega-promoted):** No backtest artifact — cannot evaluate.

---

## 6. Recommended Merge Decisions

1. **MERGE:** `keltner_fresh_break_reversion` (Kimi) — ship to paper-flag with n=154 backtest evidence and 50% Wilson LB. Low risk, highest-quality new candidate. Put `cmo_extreme_reversion` and `mfi_extreme_reversion` behind it on paper-flag too.
2. **PAPER-FLAG (do NOT merge to live):** `crypto_bb_squeeze_breakout_momentum` (PR #260) — high avg but n=21, needs live accumulation before risking capital.
3. **HOLD PR #260 broad merge:** The 20+ strategies are yfinance-universe screened, not live-pool. Merge the framework + comparison script but gate each strategy individually on paper-flag until live n ≥ 30.
4. **HOLD PR #259:** Framework is fine; request donchian_adx meta.json before counting as a strategy addition.
5. **COMMISSION S2 WALK-FORWARD:** `ml_enhanced_INJUSDT_1d_B_lightgbm`, `ml_enhanced_BNBUSDT_15m_B_lightgbm`, `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` — all show W95 LB > 0.68 at 15 ≤ n < 30 and need regime-robustness checks before being called outperformers.
6. **DEMOTE:** `quan_engine_scalp` — 4316 picks at WR 29.9% and -0.167% avg is the real pain point. Consider `BLOCKED_SOURCE_SYSTEMS` expansion per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`.

---

## 7. Honest Bottom Line

After the P0 fix, the /audit baseline is **still dominated by one large losing strategy (`quan_engine_scalp`)** and a long tail of fragmented ML variants, most under-powered (n < 15). **No existing strategy robustly outperforms** (Bonferroni-strict). **No new candidate robustly outperforms** either, though `keltner_fresh_break_reversion` is within arm's reach. The V3 playbook's "zero combos pass Wilson-Bonferroni > 50%" finding, re-run against the restored 165-strategy tracking set, **still holds** — it was not merely an artifact of the broken 5-strategy sample.

**The outperformer hunt is not yet won. The best action is to keep the incubator running: paper-flag Kimi's Keltner Fresh-Break, commission S2 walk-forward on the three promising ML micro-strategies, and let live n accumulate on PR #260's top-5 candidates.**

---

_Reproducible analysis: `tmp_analysis/run_analysis.py` (not committed — throwaway)._

---

## Review feedback — Cursor agent (2026-04-19)

1. **Definitions locked:** “Outperform” should always name the **baseline** (validated closed pool, smart gate counterfactual, or Bonferroni Wilson). This doc does that well — keep that discipline when PR titles claim “outperform.”
2. **Fragmented `strategy_performance`:** The 165-row / low-n-per-row issue is a **product** problem: consider aggregating ml_enhanced variants under a **parent strategy + symbol** key for reporting without losing lineage.
3. **PR #260 yfinance vs live:** The separation is correct. Next step for any candidate promotion: **export aligned daily returns** and run [correlation_prune_strategies.py](../baby_strategies/correlation_prune_strategies.py) against live emitters.
4. **Kimi Keltner:** “Right at the bar” means **paper-flag + forward accumulation**, not merge-to-live — matches factory intent; state S-stage explicitly in the next edit.
5. **RENDER / INJ / DYDX:** S2 walk-forward + **stress window** (e.g. FTX week, 2022 Q2) should be a checklist item, not optional narrative.
