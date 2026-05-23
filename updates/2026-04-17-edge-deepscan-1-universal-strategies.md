# Edge Deep Scan #1 — Universal Strategies per Asset Class

**Date:** 2026-04-17  
**Source:** `audit_dashboard/data/dashboard_data.json` (3,500 closed picks; 1,812 leaderboard rows; 292 backtest_vs_forward rows). Read-only audit.  
**Method:** Excluded FORCE_CLOSED flat trades (|pnl_pct| < 0.05; 21.0% of all closed picks; 54.3% of COMMODITY). WR / PF computed from `recent_closed`. Decay & kill metrics taken from `leaderboard.fwd_*` snapshots.

---

## Executive Summary (operator-facing)

- **What works:** Only **CRYPTO and EQUITY have multiple universal strategies** that beat 55% WR across 5+ symbols. The single most durable cross-symbol edge is `strong consensus (alpha_engine, ml_crypto_predictor)` at 90.8% WR, n=98, 25 symbols, PF 14.4. In equities, momentum scouts (`rs-breakout-scout`, `vol-contraction-scout`, `Breakout Momentum`) print 60–75% WR across 7+ tickers.
- **What doesn't:** **FOREX, COMMODITY, ETF, BOND have effectively no validated edge.** COMMODITY is dominated by a single strategy (`futures_momentum`, 87% of picks) with 54.3% flat rate and 46.7% real WR. ETF (n=63) and BOND (n=17) are below statistical sufficiency — every "result" is noise.
- **What to backtest:** The top backtest priorities are FOREX `connors_rsi2` (bt_wr 67.6%, n=866) and `macd_divergence` (bt_wr 67.4%, n=513) — both have <10 forward trades. Equities also need broader forward coverage: 82 of 108 equity strategies have <10 forward trades.

---

## 1. Top Strategies per Asset Class (post-flat)

### CRYPTO  (1,873 picks; 50.9% headline WR)
Filter: n_closed ≥ 10, distinct_symbols ≥ 3, max(realized_pf, snapshot_fwd_pf) ≥ 1.0.

| Strategy | n | Symbols | WR% | PF | Flat% | Notes |
|---|---:|---:|---:|---:|---:|---|
| strong consensus (alpha_engine, ml_crypto_predictor) | 98 | 25 | **90.8** | 14.41 | 3.0 | Best universal; 17 symbols at 55%+ WR |
| ml_crypto_predictor | 116 | 4 | 79.3 | 5.91 | 0.9 | XRPUSDT 100% (n=31), POLUSDT 100% (n=30) — symbol-narrow but lethal |
| st_obv_support_divergence | 96 | 17 | **72.9** | 6.68 | 1.0 | 14/17 symbols >55% WR — true universal |
| st_multi_day_momentum | 31 | 6 | 61.3 | 3.27 | 0.0 | APTUSDT 100% (n=8) gem |
| macd_rsi_confluence | 13 | 6 | 53.8 | 1.73 | 13.3 | Borderline; flat rate elevated |
| ensemble (mercury2) | 32 | 15 | 53.1 | 4.10 | 0.0 | Wide diversity, modest WR but PF strong |
| st_fear_greed_contrarian | 271 | 18 | 52.4 | 2.31 | 1.5 | Largest sample; 7 universal-quality symbols |
| luxalgo_confluence | 128 | 14 | 50.8 | 1.45 | 0.0 | Marginal; only 5 symbols >55% |
| signal_engine_momentum_mut | 10 | 6 | 50.0 | 1.57 | 0.0 | Small sample |
| claude_ml_moderate_mut | 13 | 3 | 46.2 | 1.29 | 0.0 | Min-symbol threshold |

### EQUITY  (346 picks; 49.9% headline WR)

| Strategy | n | Symbols | WR% | PF | Source |
|---|---:|---:|---:|---:|---|
| stocks_rsi2_pullback | 8 | 5 | **87.5** | 5.14 | rsi2 (need n≥10 to confirm) |
| donchian-stock-breakout | 5 | 5 | 80.0 | 8.92 | small sample |
| rs-breakout-scout | 12 | 7 | **75.0** | 5.85 | kimi_riseoftheclaw — high confidence |
| vol-contraction-scout | 11 | 7 | **72.7** | 3.67 | kimi_riseoftheclaw |
| post-earnings-rev-scout | 8 | 7 | 62.5 | 1.16 | small sample but wide |
| quality-minus-junk | 15 | 2 | 60.0 | 1.59 | symbol-narrow (CVX, XOM) |
| Breakout Momentum | 37 | 7 | 59.5 | 1.72 | stocks_competition — robust |
| Meta Learner | 14 | 8 | 50.0 | 1.50 | stocks_competition |
| rsi-divergence-scout | 10 | 4 | 50.0 | 2.56 | borderline |
| Bollinger MR | 50 | 23 | 48.0 | 1.60 | widest equity coverage |

### FOREX  (785 picks; 27.1% headline WR — 61% flat rate on copy_trader)

| Strategy | n | Symbols | WR% | PF | Flat% | Notes |
|---|---:|---:|---:|---:|---:|---|
| Bollinger MR | 12 | 4 | **66.7** | 2.62 | 14.3 | Same strat works in EQUITY too |
| forex-rsi-ema-scout | 15 | 6 | 60.0 | 2.81 | 0.0 | kimi_riseoftheclaw |
| forex_rsi2_mean_reversion | 184 | 12 | 54.9 | 4.09 | **61.5** | High flat rate hides true performance |
| Breakout Momentum | 31 | 4 | 35.5 | 0.34 | 3.1 | KILL candidate |
| community_london_breakout_v2_forex | 8 | 4 | 0.0 | 0.0 | – | KILL — 0% WR n=8 |

### COMMODITY  (416 picks; 24.9% headline; **54.3% flat rate**)

| Strategy | n_real | Symbols | WR% | PF | Notes |
|---|---:|---:|---:|---:|---|
| futures_momentum | 180 | 8 | 46.7 | 1.29 | **The only strategy with usable sample.** 87% of all commodity picks. Symbol-concentrated (SI=F, HG=F, GC=F, PL=F = metals only) |

**Critical:** No commodity strategy passes 50% WR with n≥10. The asset class is single-strategy single-niche (metals only). Need diversification before any real money.

### ETF  (63 picks; below statistical sufficiency)
- `quality-minus-junk` n=10 sym=1 WR 50% PF 0.94 (1 symbol = not universal)
- `intermarket-flow-scout` n=7 WR 42.9% PF 0.99
- **Conclusion:** No ETF strategy meets even baseline filters. Needs deliberate backtest expansion.

### BOND  (17 picks; statistically void)
- `futures_momentum` on a single bond symbol n=5 WR 60% (noise)
- **Conclusion:** Bond pipeline is dormant. Either decommission or build a real backtest set.

---

## 2. Universal Strategies (>55% WR across ≥5 symbols, min 3 trades each)

### CRYPTO — 5 candidates
| Strategy | Total n | Symbols >55% WR | Universal score |
|---|---:|---:|---|
| strong consensus (alpha_engine, ml_crypto_predictor) | 98 | **17** | Tier-1 universal (deploy w/ live capital) |
| st_obv_support_divergence | 96 | 14 | Tier-1 universal |
| st_fear_greed_contrarian | 271 | 7 | Tier-2 (large sample, modest edge) |
| luxalgo_confluence | 128 | 5 | Tier-3 borderline |
| st_rsi_momentum_confluence | 86 | 5 | Tier-3 (overall WR 43%, edge is symbol-conditional) |

### EQUITY / FOREX / COMMODITY / ETF / BOND — **0 universal strategies**
None pass the 5-symbol threshold at >55% WR with min-3-trade-per-symbol confirmation. All non-crypto edge is symbol-specific.

---

## 3. Symbol-Specific Gems (WR ≥ 70% on n ≥ 5 — rare-but-amazing)

### CRYPTO (top 10 of 30 found)
| Strategy | Symbol | n | WR% | Avg PnL% |
|---|---|---:|---:|---:|
| ml_crypto_predictor | XRPUSDT | 31 | **100.0** | +5.77 |
| ml_crypto_predictor | POLUSDT | 30 | **100.0** | +3.97 |
| st_multi_day_momentum | APTUSDT | 8 | 100.0 | +6.49 |
| strong consensus (a_e, ml_crypto_pred) | APEUSDT | 7 | 100.0 | +3.34 |
| st_obv_support_divergence | OPUSDT | 7 | 100.0 | +2.68 |

### EQUITY
| Strategy | Symbol | n | WR% | Avg PnL% |
|---|---|---:|---:|---:|
| Breakout Momentum | CVX | 9 | 88.9 | +3.66 |
| Breakout Momentum | XOM | 10 | 80.0 | +3.44 |
| quality-minus-junk | CVX | 7 | 71.4 | +1.58 |

**Pattern:** All equity gems concentrate on energy mega-caps (CVX, XOM). Suggests a sector/regime tailwind, not a strategy edge.

### FOREX
| Strategy | Symbol | n | WR% | Avg PnL% |
|---|---|---:|---:|---:|
| Bollinger MR | FXF | 6 | 83.3 | +0.18 |
| forex_rsi2_mean_reversion | EURGBP=X | 15 | 73.3 | +0.05 |

### COMMODITY / ETF / BOND
None.

---

## 4. Backtest Gaps (per asset class)

| Asset Class | Total LB strats | bt_trades < 30 | fwd_trades < 10 | Action |
|---|---:|---:|---:|---|
| CRYPTO | 264 | 243 | 89 | Most have BT but lack fwd |
| EQUITY | 108 | **108** | **82** | Entire equity ledger lacks BT depth |
| FOREX | 57 | 55 | 38 | BT is good for connors_rsi2 / macd_divergence — push them to forward |
| COMMODITY | 20 | 20 | 14 | Build BT before claiming edge |
| ETF | 20 | 20 | 18 | Class is essentially un-backtested |
| BOND | 2 | 2 | 0 | Pipeline missing |

### Top Backtest Priorities (good BT, missing forward)

| # | Strategy | Asset Class | bt_wr | bt_trades | bt_pf | fwd_trades | Why |
|---|---|---|---:|---:|---:|---:|---|
| 1 | **connors_rsi2** | FOREX | 67.6 | 866 | 1.41 | 9 | Massive BT, near zero forward — highest sample-quality candidate in repo |
| 2 | **macd_divergence** | FOREX | 67.4 | 513 | 1.40 | 6 | Same profile — proven on paper, untested live |
| 3 | EQUITY momentum scouts (rs-breakout, vol-contraction, donchian) | EQUITY | n/a | <30 | n/a | 5–12 | Working in early forward but have NO bt depth — must run full historical BT before scaling |
| 4 | Any COMMODITY non-`futures_momentum` strategy | COMMODITY | n/a | <30 | n/a | <10 | Single-strategy concentration risk; need regime-aware alts |
| 5 | ETF cross-asset momentum (`intermarket-flow-scout`, `pairs-trading`) | ETF | n/a | <30 | n/a | <10 | Asset class effectively un-tested |

---

## 5. Decay Flags (bt_wr − fwd_wr > 15pp on n_fwd ≥ 20)

These strategies look good on the leaderboard's BT column but are **bleeding live**:

| Strategy | bt_wr | fwd_wr | Decay (pp) | n_fwd | Verdict |
|---|---:|---:|---:|---:|---|
| crypto_soc_proxy_decoupling_a03_v1 | 66.0 | 34.0 | **−32.0** | 53 | KILL |
| crypto_soc_regime_filters_a03_v1 | 66.0 | 40.5 | −25.5 | 37 | KILL |
| crypto_soc_mtf_orb_pivots_a10_v1 | 51.0 | 26.1 | −24.9 | 23 | KILL |
| crypto_adx_pullback_trendresume_v1 | 63.0 | 38.5 | −24.5 | 52 | KILL |
| crypto_soc_mtf_orb_pivots_a03_v1 | 56.0 | 34.4 | −21.6 | 32 | KILL |
| crypto_soc_mtf_orb_pivots_a05_v1 | 51.0 | 29.6 | −21.4 | 27 | KILL |
| crypto_choppiness_regime_switch_v1 | 58.0 | 38.3 | −19.7 | 60 | KILL |
| crypto_soc_delta_divergence_a03 / a07 / a02_v1 | 55–60 | 37–43 | 16–18 | 80–104 | DEMOTE & MUTATE first per `MUTATION_THREE_AXIS_PROTOCOL.md` |

**Note:** All confirmed decay rows live on the crypto SOC (`crypto_soc_*`) family. The `crypto_soc_mtf_orb_pivots` siblings (a03/a04/a05/a10) all decay — likely a structural BT/forward env mismatch, not symbol-specific.

---

## 6. Recommended Kill / Demote List

Strategies with `fwd_pf < 0.7` on n_fwd ≥ 20 OR confirmed decay >15pp (excluding duplicates):

### Immediate KILL (fwd_pf ≤ 0.5 with material sample)
| Asset Class | Strategy | fwd_pf | fwd_wr | n_fwd | DD% |
|---|---|---:|---:|---:|---:|
| CRYPTO/SOC | crypto_soc_regime_filters_a05_v1 | 0.0 | 54.1 | 37 | 1.0 |
| CRYPTO/SOC | crypto_soc_orderflow_absorption_a07_v1 | 0.0 | 43.6 | 181 | 0.62 |
| CRYPTO/SOC | crypto_shortterm_nr_er_cci_ignition_v1 | 0.0 | 40.5 | 79 | 1.07 |
| CRYPTO/SOC | crypto_soc_delta_divergence_a09_v1 | 0.0 | 37.3 | 67 | 1.12 |
| CRYPTO/SOC | crypto_soc_mtf_orb_pivots_a03_v1 / a04_v1 | 0.0 | 29–34 | 31–32 | <1 |
| CRYPTO/SOC | crypto_soc_delta_divergence_a06_v1 | 0.17 | 44.7 | 94 | 2.28 |
| CRYPTO | quan_engine_position | 0.0 | 0 | 26 | **103.75** |
| CRYPTO | ml_breakout | 0.0 | 0 | 21 | 0.21 |
| CRYPTO | multi_period_rsi_confluence_doge | 0.0 | 0–50 | 36–37 | 10.0 |
| CRYPTO | BTC 4H RSI+MACD Confluence | 0.17 | 9.5 | 21 | **36.0** |
| CRYPTO | macd_crossover (vanilla) | 0.35 | 27.6 | 58 | **90.72** |
| CRYPTO | claude_gainer_1h | 0.41 | 39.0 | 287 | **651.11** |
| CRYPTO | ml_enhanced_HBARUSDT_1d_D_ensemble_stack | 0.12 | 30.0 | 20 | 61.17 |
| CRYPTO | ml_enhanced_AVAXUSDT_15m_D_ensemble_stack | 0.48 | 40.9 | 22 | 17.6 |
| FOREX | forex_rsi2_mean_reversion (full leaderboard row) | 0.33 | 55.2 | 32 | 0.49 |

**Important:** Per `CLAUDE.md` and `MUTATION_THREE_AXIS_PROTOCOL.md`, do NOT expand `BLOCKED_SOURCE_SYSTEMS` without first running mutation analysis (`tools/mutation_analysis.py`). The decay families above (`crypto_soc_*`, `crypto_adx_pullback_trendresume_v1`, `crypto_choppiness_regime_switch_v1`) are ideal mutation targets — the BT alpha exists, the forward env is breaking it.

**Inconsistency to investigate:** The FOREX leaderboard reports `forex_rsi2_mean_reversion` fwd_pf=0.33 / fwd_wr=55.2 / n=32 (KILL), but our recent_closed analysis shows the same strategy at 54.9% WR, PF 4.09 across 184 trades. Likely the leaderboard row keys on a partition/symbol slice. Reconcile before pulling the trigger — see open issue #173 (forward_validator.py re-keying).

---

## 7. Cross-Asset-Class Universal Strategies

**Question:** Does any strategy class win across multiple non-crypto asset classes?

**Answer:** Almost no. Only **one** strategy passes the test with n≥10 in 2+ asset classes at WR≥50%:

| Strategy | Asset Classes | Verdict |
|---|---|---|
| quality-minus-junk | EQUITY (60% WR n=15 PF 1.59) + ETF (50% WR n=10 PF 0.94) | Marginal — ETF leg breakeven |

**Strategies that traded multiple asset classes but failed cross-class durability:**
- `Bollinger MR`: EQUITY 48% (n=50, 23 syms, PF 1.60) **+ FOREX 66.7% (n=12, 4 syms, PF 2.62)**. EQUITY leg fails 50% WR cutoff but the dual-AC presence is real — **promising mean-reversion candidate** worth deeper backtest.
- `Breakout Momentum`: EQUITY 59.5% n=37 PF 1.72 vs FOREX 35.5% n=31 PF 0.34 — strong in equities, broken in forex. Not universal.
- `rs-breakout-scout`, `vol-contraction-scout`: Only material in EQUITY despite ETF/BOND tags.

### Recommended cross-AC research bets
1. **Bollinger MR / RSI2 mean-reversion family** — only architecture showing real signal in both equity and forex; build a unified RSI2/Bollinger backtest harness across EQUITY + FOREX + ETF.
2. **Breakout Momentum** — works for equities but not forex; explore why (volatility regime? carry effects?) before discarding.
3. **`quality-minus-junk` factor** — extend ETF coverage (current n=10, single symbol).

---

## 8. Operator Action List (priority-ordered)

1. **Promote to live capital (CRYPTO only):** `strong consensus (alpha_engine, ml_crypto_predictor)`, `st_obv_support_divergence`, `ml_crypto_predictor` (XRPUSDT/POLUSDT bias).
2. **Promote to expanded forward (EQUITY):** `rs-breakout-scout`, `vol-contraction-scout`, `Breakout Momentum` — all need n>30 and BT depth before live.
3. **Expand backtest:** `connors_rsi2` and `macd_divergence` (FOREX) — already have 500+ BT trades, push to forward.
4. **Demote-and-mutate (do NOT kill yet):** `crypto_soc_*` family — large BT alpha, structural forward decay; run `tools/mutation_analysis.py` per `MUTATION_THREE_AXIS_PROTOCOL.md`.
5. **Hard kill once mutation budget exhausted:** `quan_engine_position` (DD 103%), `claude_gainer_1h` (DD 651%), `BTC 4H RSI+MACD Confluence` (9.5% WR), `community_london_breakout_v2_forex` (0% WR n=8).
6. **Build out:** ETF and BOND pipelines are statistically void (n=63 / n=17). Either invest in a real backtest set or decommission.
7. **Investigate:** Forex `forex_rsi2_mean_reversion` divergence between leaderboard fwd_pf=0.33 and recent_closed PF=4.09 — issue #173 forward_validator.py re-keying.

---

*Generated by edge-deepscan-1. All metrics post-flat (|pnl_pct|≥0.05). Snapshot read-only — no code edited.*
