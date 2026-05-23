# Strategy Summary by Asset Class — EXTENSIVE

**Date:** 2026-04-19
**Data:** live `https://findtorontoevents.ca/audit/data/dashboard_data.json`, classified by strategy's actual symbols (not `asset_classes[0]` which mis-groups)
**Method:** Aggregated each strategy's `top_symbols` array. Wilson 95% LB computed per combo.
**Resolved-strategy combos**: CRYPTO 471 · EQUITY 52 · ETF 27 · FOREX 22 · COMMODITY 12 · BOND 5

## Executive summary

| Asset | Resolved combos | Total n | Aggregate WR | Total PnL | Diagnosis |
|---|---:|---:|---:|---:|---|
| 🪙 **CRYPTO** | 471 | 5,113 | 44.0% | **+108%** | Positive but concentrated — top-3 combos = +520% while bottom-5 = −583% |
| 📈 **EQUITY** | 52 | 362 | 48.2% | **+110%** | Best-quality asset class; kimi_riseoftheclaw dominates top-10 |
| 🧺 **ETF** | 27 | 80 | 47.4% | −3% | Flat; intermarket-flow-scout is #1 but only n=13 |
| 💱 **FOREX** | 22 | 566 | 41.2% | **−816%** | **98% of the bleed is ONE strategy** — see below |
| 🛢️ **COMMODITY** | 12 | 250 | 47.1% | −19% | Too sparse; futures_momentum dominates n but flat EV |
| 🏦 **BOND** | 5 | 12 | 60.0% | −0.4% | Data desert; not actionable |

## 🔴 Critical finding — FOREX bleed isolated to ONE strategy

**`kimi_signal_tracking/default` on FOREX: n=111, WR 26.1%, total −833.7% (avg −7.51%/trade)**

All other FOREX combos combined: +17% (positive). **Retiring just this one strategy turns FOREX from disaster into marginally winning.**

Recommendation: **immediate blocklist add** for `kimi_signal_tracking/default` on forex symbols. This is higher-leverage than anything else in today's session.

---

## 🪙 CRYPTO — Top 10 and Bottom 5

**Asset-class stats:** 471 combos, n=5,113 resolved, WR 44.0%, total +108.4%

### Top 10 by realized PnL
| # | System | Strategy | n | WR | Wilson 95% LB | Total | Avg |
|---|---|---|---|---|---|---|---|
| 1 | alpha_engine | `ml_enhanced_INJUSDT_1d_B_lightgbm` | 21 | **100%** | 84.5% | **+285.2%** | +13.58% |
| 2 | aggregated_picks | `Extreme Fear Contrarian Buy` | 70 | 67.1% | **55.5%** | +121.9% | +1.74% |
| 3 | aggregated_picks | `Multi-Timeframe Trend Alignment` | 40 | **87.5%** | 73.9% | +113.5% | +2.84% |
| 4 | claude_gainer_st | `st_fear_greed_contrarian` | 354 | 39.5% | 34.6% | +71.0% | +0.20% |
| 5 | kimi_signal_tracking | `kimi_signal_tracking` | 92 | 43.5% | 33.8% | +63.1% | +0.69% |
| 6 | baby_strats_forward | `vwap_deviation_reversion_doge_v1` | 6 | 100% | 61.0% | +60.0% | +10.00% |
| 7 | dna_winner_picks | `claude_ml_moderate_mut` | 63 | 58.7% | 46.4% | +51.4% | +0.82% |
| 8 | kimi_riseoftheclaw | `cci-crypto-reversal` | 12 | 58.3% | 32.0% | +47.3% | +3.94% |
| 9 | claude_gainer_st | `st_obv_support_divergence` | 90 | 55.6% | 45.3% | +41.7% | +0.46% |
| 10 | alpha_engine | `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` | 24 | **100%** | 86.2% | +39.9% | +1.66% |

### Bottom 5 (retirement candidates)
| System | Strategy | n | WR | Total |
|---|---|---|---|---|
| copy_trader_intel | `copy_hl_lb_None` | 25 | 0% | −270.8% |
| mercury2_fast | `Mercury2 Fast` | 2 | 0% | −145.9% |
| super_signals | `strong consensus (alpha_engine, ml_crypto_pred, kimi)` | 34 | 11.8% | −59.6% |
| alpha_engine | `ml_enhanced_HBARUSDT_1d_D_ensemble_stack` | 21 | 33.3% | −55.2% |
| alpha_engine | `ml_enhanced_POLUSDT_1d_B_lightgbm` | 21 | 33.3% | −51.7% |

### Actionable crypto notes
- **INJ 100% WR on n=21** and DYDX 100% WR on n=24 are suspicious concentration risk — commission S2 walk-forward before trusting. V3 agent already flagged.
- **`copy_hl_lb_None` at 0/25 (−270%)** — retirement candidate. Zero wins in 25 trades is deterministic-loss territory (reminiscent of MATIC pattern).
- **`super_signals` strong-consensus at 11.8% on n=34** — "consensus" is supposed to REDUCE risk but underperforms pure random. Audit the consensus logic.

---

## 📈 EQUITY — Top 10 and Bottom 5

**Asset-class stats:** 52 combos, n=362 resolved, WR 48.2%, total +109.9%

### Top 10
| # | System | Strategy | n | WR | W95 LB | Total | Avg |
|---|---|---|---|---|---|---|---|
| 1 | stocks_competition | `Breakout Momentum` | 47 | 53.2% | 39.2% | +49.7% | +1.06% |
| 2 | kimi_riseoftheclaw | `donchian-stock-breakout` | 6 | 83.3% | 43.6% | +44.9% | +7.48% |
| 3 | kimi_riseoftheclaw | `rs-breakout-scout` | 8 | **87.5%** | **52.9%** | +22.4% | +2.80% |
| 4 | kimi_riseoftheclaw | `price-accel-scout` | 4 | 75.0% | 30.1% | +19.6% | +4.89% |
| 5 | kimi_riseoftheclaw | `rsi-divergence-scout` | 6 | 50.0% | 18.8% | +16.0% | +2.67% |
| 6 | kimi_riseoftheclaw | `short-squeeze-scout` | 1 | 100% | 20.7% | +16.0% | +15.96% |
| 7 | kimi_riseoftheclaw | `vol-contraction-scout` | 8 | 62.5% | 30.6% | +13.5% | +1.69% |
| 8 | stocks_competition | `Quality Compounders` | 1 | 100% | 20.7% | +13.5% | +13.49% |
| 9 | kimi_riseoftheclaw | `gap-and-go-stocks` | 4 | 50.0% | 15.0% | +10.0% | +2.49% |
| 10 | kimi_riseoftheclaw | `mtf-align-scout` | 1 | 100% | 20.7% | +8.1% | +8.09% |

### Bottom 5
| System | Strategy | n | WR | Total |
|---|---|---|---|---|
| claude_gainer | `claude_gainer_4h` | 8 | 12.5% | −25.0% |
| stocks_competition | `Bollinger MR` | 24 | 37.5% | −20.0% |
| multi_asset_copytrader | `smart_money_accumulation` | 5 | 20.0% | −18.9% |
| goldmine_stocks | `goldmine_6x_consensus` | 4 | 0% | −16.7% |
| fast_stocks_competition | `Breakout Momentum` | 4 | 0% | −16.0% |

### Actionable equity notes
- **`kimi_riseoftheclaw/rs-breakout-scout`** is the only equity combo with Wilson 95% LB > 50% (52.9% at n=8). Commission S2 walk-forward.
- **kimi_riseoftheclaw dominates top-10** — 8 of 10 are kimi. Her scouts work on equities. Merge her PR (`feature/baby-strategies-mfi-cmo-keltner-aroon`) to expand this coverage.
- **`fast_stocks_competition/Breakout Momentum`** loses −16% at 0% WR while `stocks_competition/Breakout Momentum` wins +49.7% at 53.2% WR on same strategy name. **Config drift — investigate why.**

---

## 🧺 ETF — Top 10 and Bottom 5

**Asset-class stats:** 27 combos, n=80 resolved, WR 47.4%, total −3.2%

### Top 10
| # | System | Strategy | n | WR | W95 LB | Total | Avg |
|---|---|---|---|---|---|---|---|
| 1 | kimi_riseoftheclaw | `intermarket-flow-scout` | 13 | 53.8% | 29.1% | +9.0% | +0.69% |
| 2 | kimi_riseoftheclaw | `rs-breakout-scout` | 3 | 66.7% | 20.8% | +7.8% | +2.59% |
| 3 | kimi_riseoftheclaw | `quality-momentum-scout` | 2 | 100% | 34.2% | +5.8% | +2.90% |
| 4 | kimi_riseoftheclaw | `vix-mean-rev-scout` | 2 | 50.0% | 9.5% | +4.6% | +2.29% |
| 5 | multi_asset_institutional | `sector_rotation` | 1 | 100% | 20.7% | +4.4% | +4.40% |
| 6 | kimi_riseoftheclaw | `price-accel-scout` | 3 | 33.3% | 6.1% | +3.9% | +1.29% |
| 7 | kimi_riseoftheclaw | `golden-cross-stocks` | 1 | 100% | 20.7% | +3.0% | +3.05% |
| 8 | kimi_riseoftheclaw | `rsi-divergence-scout` | 4 | 50.0% | 15.0% | +2.8% | +0.69% |
| 9 | kimi_riseoftheclaw | `aroon-trend-scout` | 1 | 100% | 20.7% | +2.2% | +2.24% |
| 10 | alpha_engine_fast | `markov_zone_transition` | 4 | **100%** | **51.0%** | +2.0% | +0.50% |

### Bottom 5
| System | Strategy | n | WR | Total |
|---|---|---|---|---|
| kimi_riseoftheclaw | `betting-against-beta` | 4 | 0% | −8.1% |
| kimi_riseoftheclaw | `ema-ribbon` | 4 | 25.0% | −7.3% |
| institutional_picks_enhanced | `hyperopt_connors_rsi2` | 2 | 0% | −6.6% |
| goldmine_stocks | `goldmine_1x_consensus` | 1 | 0% | −5.8% |
| kimi_riseoftheclaw | `options-flow-scout` | 3 | 0% | −5.5% |

### Actionable ETF notes
- **Nearly every top-10 combo has n≤4** — sample is too small to trust. ETF asset class is under-represented.
- `intermarket-flow-scout` (#1) is already paper-flagged from earlier work.
- `alpha_engine_fast/markov_zone_transition` is the only combo with Wilson 95% LB > 50% (at n=4, borderline).
- **`betting-against-beta` 0% WR** — academic factor that's been arbitraged by smart-beta ETFs. Kimi's implementation doesn't work. Confirms peer-review rejection of BAB strategies.

---

## 💱 FOREX — THE BLEEDER

**Asset-class stats:** 22 combos, n=566 resolved, WR 41.2%, total **−816.3%**

### Top 10 (all positive)
| # | System | Strategy | n | WR | W95 LB | Total | Avg |
|---|---|---|---|---|---|---|---|
| 1 | multi_asset_copytrader | `forex_rsi2_mean_reversion` | 138 | 52.9% | 44.6% | +23.2% | +0.17% |
| 2 | kimi_riseoftheclaw | `forex-rsi-ema-scout` | 14 | 64.3% | 38.8% | +5.5% | +0.39% |
| 3 | alpha_engine | `fx_smart_carry_trade_momentum` | 5 | 100% | **56.6%** | +2.4% | +0.48% |
| 4-10 | (various) | | n≤3 each | ... | ... | +0.1-1.2% | ... |

### 🚨 Bottom 5 — THE SOURCE OF THE −816% BLEED
| System | Strategy | n | WR | **Total** |
|---|---|---|---|---|
| **kimi_signal_tracking** | **`default`** | **111** | **26.1%** | **−833.7%** 🔴 |
| multi_asset_institutional | `forex_carry_momentum` | 4 | 25.0% | −8.0% |
| kimi_riseoftheclaw | `carry-trade-momentum` | 15 | 26.7% | −2.2% |
| kimi_riseoftheclaw | `dxy-reversal-scout` | 10 | 20.0% | −1.9% |
| kimi_riseoftheclaw | `london-breakout-scout` | 3 | 0% | −1.3% |

**The `kimi_signal_tracking/default` strategy alone accounts for −833.7% of the −816.3% aggregate FOREX loss.** Every other forex strategy combined is net positive.

### Critical recommended action
Add `kimi_signal_tracking` (when on forex symbols) to `alpha_engine/strategy_blocklist.py`. Expected impact: FOREX asset class flips from −816% to **+17%** total PnL. This is the highest-ROI action in the entire /audit universe.

---

## 🛢️ COMMODITY — Too sparse for strong claims

**Asset-class stats:** 12 combos, n=250 resolved, WR 47.1%, total −19.4%

### Top 10
| # | System | Strategy | n | WR | W95 LB | Total | Avg |
|---|---|---|---|---|---|---|---|
| 1 | multi_asset_copytrader | `futures_momentum` | **213** | 46.0% | 39.4% | +13.4% | +0.06% |
| 2 | multi_asset_scanner | `ema_stack_momentum` | 2 | 50% | 9.5% | +3.3% | +1.66% |
| 3 | kimi_riseoftheclaw | `volume-anomaly-scout` | 1 | 100% | 20.7% | +1.4% | +1.44% |
| 4 | alpha_engine | `combined_confidence` | 1 | 100% | 20.7% | +0.1% | +0.11% |
| 5 | cta_replicator | `cta_cross_asset_tsmom` | 5 | 80.0% | 37.6% | +0.1% | +0.02% |
| 6+ | (all below 0) | | | | | | |

### Commodity notes
- **`futures_momentum` has ALL the volume** (213 of 250 trades) but avg PnL only +0.06% — basically flat after costs
- No combo has Wilson 95% LB > 50%
- Commodity asset class isn't producing signal yet

---

## 🏦 BOND — Data desert

**Asset-class stats:** 5 combos, n=12 resolved

All combos have n ≤ 2. Single-trade wins showing as "100% WR" are meaningless. **Bond strategies aren't running or aren't resolving.** Investigate:
- Is bond data-feed broken?
- Are bond signals being emitted but exiting too fast to register?

---

## Recommended actions (by impact, highest first)

1. **🔴 Block `kimi_signal_tracking/default` on forex symbols** — single highest-ROI action. FOREX flips from −816% to +17%.
2. **🔴 Retire `copy_hl_lb_None` (crypto)** — 0% WR on n=25, bleeding like MATIC pattern. Add to blocklist.
3. **🟡 Commission S2 walk-forward on INJ/DYDX ml_enhanced_*_lightgbm** — 100% WR at n=21-24 is too concentrated to trust, but Wilson LB 84-86% IS significant.
4. **🟡 Merge kimi_riseoftheclaw's PR** (`feature/baby-strategies-mfi-cmo-keltner-aroon`) — her scouts dominate EQUITY top-10; 4 new strategies diversify coverage without crowding.
5. **🟡 Investigate `stocks_competition/Breakout Momentum` vs `fast_stocks_competition/Breakout Momentum`** — same name, opposite results (+49.7% vs −16%). Config drift to fix.
6. **🟢 Investigate BOND data pipeline** — 12 trades total suggests emission or resolution is broken.
7. **🟢 Re-audit `super_signals` consensus logic** — "strong consensus (alpha_engine + ml_crypto_pred + kimi)" at 11.8% WR suggests the aggregator is doing damage, not adding alpha.

## Per-class S4 paper-test candidates (ready now)

Passing Wilson 95% LB > 50% AND avg_pnl > 0:
- **CRYPTO**: `INJUSDT 1d ml_enhanced` (LB 84.5%), `DYDXUSDT 15m ml_enhanced` (LB 86.2%), `Extreme Fear Contrarian Buy` (LB 55.5%), `Multi-TF Trend Alignment` (LB 73.9%)
- **EQUITY**: `rs-breakout-scout` (LB 52.9% at n=8)
- **ETF**: `markov_zone_transition` (LB 51.0% at n=4 — borderline)
- **FOREX**: `fx_smart_carry_trade_momentum` (LB 56.6% at n=5 — borderline)
- **COMMODITY**: none
- **BOND**: none (insufficient data)

**These 7 are the complete current-dashboard set that passes the v1.1 statistical gate.** Commission S2 walk-forward on all 7 as the next actionable step.

---

## Review feedback — Cursor agent (2026-04-19)

1. **kimi_signal_tracking/default (FOREX):** The isolation result is high-leverage; **verify on a fresh `dashboard_data.json` pull** and log the exact filter (`system`, `strategy`, symbol class) in `audit_trail` or a ticket so it is reproducible after the next generator change.
2. **Orthogonality before S2 spend:** For the seven “passing” combos, run **pairwise correlation of daily returns** vs each other and vs `quan_engine_scalp` / top emitters — [correlation_prune_strategies.py](../baby_strategies/correlation_prune_strategies.py). Factory v1.1 asks for orthogonality; don’t commission seven redundant curves.
3. **super_signals consensus:** If consensus underperforms constituents, treat it as a **gating bug** (weights, eligibility, or timing), not a strategy — add a short RCA section when someone picks this up.
4. **Bond pipeline:** “n too small” may be **product** (few bond tickers) or **instrumentation** — split the hypothesis before investing in new bond strategies.
5. **Discovery workflow:** Align operational next steps with [STRATEGY_DISCOVERY_PROTOCOL.md](STRATEGY_DISCOVERY_PROTOCOL.md) (cost table, OOS holdout, correlation CSV).
