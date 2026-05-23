# Strategy Summary by Asset Class — findtorontoevents.ca/audit

**Date:** 2026-04-19
**Data source:** live `dashboard_data.json` (symbol-classified, not `asset_classes[0]` — which mis-groups kimi_riseoftheclaw's crypto picks under BOND)
**Method:** Aggregated each strategy's `top_symbols` array by the symbol's asset class

## Top-line asset-class picture

| Asset | Distinct strategies | Total trades (n) | Aggregate WR | Total realized PnL |
|---|---:|---:|---:|---:|
| **CRYPTO** | **475** | **5,113** | **44.0%** | **+108.4%** |
| **EQUITY** | 53 | 362 | 48.2% | **+109.9%** |
| **ETF** | 27 | 80 | 47.4% | −3.2% |
| **FOREX** | 33 | 566 | 41.2% | **−816.3%** 🔴 |
| **COMMODITY** | 15 | 250 | 47.1% | −19.4% |
| **BOND** | 5 | 12 | 60.0% | −0.4% |
| UNKNOWN | 4 | 219 | 44.6% | +23.3% |

### Counter-intuitive findings

1. **CRYPTO is net +108% on 5,113 trades** — not the disaster we thought yesterday. Aggregate WR 44% is below 50% but pockets of strong winners lift the total.
2. **FOREX is bleeding −816%** across 566 trades — by far the worst asset class. **This is the biggest retirement target.**
3. **EQUITY +109.9% at 48.2% WR with only 362 trades** — best risk-adjusted performance per unit of sample.
4. **ETF is essentially flat** (−3.2% on 80 trades) — validates yesterday's finding that recent 85% WR was a hot streak, not durable edge.
5. **BOND/COMMODITY universes are too small to draw conclusions** — 12 and 250 trades respectively.

## Top 3 strategies per asset class (by realized PnL)

### 🪙 CRYPTO (best asset class by total PnL)
| Rank | System / Strategy | n | WR | Total |
|---|---|---|---|---|
| 1 | alpha_engine / `ml_enhanced_INJUSDT_1d_B_lightgbm` | 21 | **100%** | **+285%** |
| 2 | aggregated_picks / `Extreme Fear Contrarian Buy` | 70 | 67.1% | +121.9% |
| 3 | aggregated_picks / `Multi-Timeframe Trend Alignment` | 40 | **87.5%** | +113.5% |

*Note: INJ 100% WR on n=21 is suspicious — likely concentrated regime-specific wins. V3 analysis recommends S2 walk-forward before trusting.*

### 📈 EQUITY (best risk-adjusted)
| Rank | System / Strategy | n | WR | Total |
|---|---|---|---|---|
| 1 | stocks_competition / `Breakout Momentum` | 47 | 53.2% | +49.7% |
| 2 | kimi_riseoftheclaw / `donchian-stock-breakout` | 6 | 83.3% | +44.9% |
| 3 | kimi_riseoftheclaw / `rs-breakout-scout` | 8 | 87.5% | +22.4% |

### 🧺 ETF (marginal)
| Rank | System / Strategy | n | WR | Total |
|---|---|---|---|---|
| 1 | kimi_riseoftheclaw / `intermarket-flow-scout` | 13 | 53.8% | +9.0% |
| 2 | kimi_riseoftheclaw / `rs-breakout-scout` | 3 | 66.7% | +7.8% |
| 3 | kimi_riseoftheclaw / `quality-momentum-scout` | 2 | 100% | +5.8% |

*Note: `intermarket-flow-scout` was paper-flagged earlier today — recent 85% was a hot streak against 52% all-time.*

### 💱 FOREX (bleeding — retire candidates)
| Rank | System / Strategy | n | WR | Total |
|---|---|---|---|---|
| 1 | multi_asset_copytrader / `forex_rsi2_mean_reversion` | 138 | 52.9% | +23.2% |
| 2 | kimi_riseoftheclaw / `forex-rsi-ema-scout` | 14 | 64.3% | +5.5% |
| 3 | alpha_engine / `fx_smart_carry_trade_momentum` | 5 | 100% | +2.4% |

**Top 3 only total +31%. The −816% bleed is from the long tail of forex strategies not in top-3.** Biggest retirement opportunity in the whole repo.

### 🛢️ COMMODITY (small sample)
| Rank | System / Strategy | n | WR | Total |
|---|---|---|---|---|
| 1 | multi_asset_scanner / `ema_stack_momentum` | 2 | 50% | +3.3% |
| 2 | multi_asset_copytrader / `futures_momentum` | 114 | 47.4% | +1.6% |
| 3 | kimi_riseoftheclaw / `volume-anomaly-scout` | 1 | 100% | +1.4% |

*n<3 for 2 of top-3 — noise.*

### 🏦 BOND (too sparse)
All strategies have n≤2. Inconclusive.

## What this tells us for "outperform current" challenge

### Clear retirement targets
- **Forex bleed −816% over 566 trades** — there's a cluster of forex strategies losing big. Run rehabilitation pipeline (cross-symbol → inverse → regime gate) on the bottom 20 forex combos before rolling out more forex strategies.
- **ETF aggregate flat** despite 27 strategies — stop adding ETF strategies until existing ones either pass Wilson LB or get retired.

### Realistic S4 candidates (from top-3 above, passing basic screen)
| Candidate | Asset | n | WR | Composite score |
|---|---|---|---|---|
| `aggregated_picks/Extreme Fear Contrarian Buy` | CRYPTO | 70 | 67.1% | Strong |
| `aggregated_picks/Multi-Timeframe Trend Alignment` | CRYPTO | 40 | 87.5% | Strong but small n |
| `stocks_competition/Breakout Momentum` | EQUITY | 47 | 53.2% | Marginal |
| `multi_asset_copytrader/forex_rsi2_mean_reversion` | FOREX | 138 | 52.9% | Only forex strategy NOT bleeding |

### Kimi's 4-strategy PR context
Looking at the table: kimi_riseoftheclaw shows up 5 times in top-3 lists (donchian-stock-breakout, rs-breakout-scout, intermarket-flow-scout, forex-rsi-ema-scout, volume-anomaly-scout) — but most have n<15. Her 4 new strategies (MFI, CMO, Keltner Fresh-Break, Aroon) would add equity/forex variants to this portfolio. **Merge her PR = diversifies asset coverage without displacing anything.**

## Recommended asset-class priorities (in order)

1. **STOP adding new FOREX strategies** — retire the bleeders first (run rehab on worst 20 combos). Expected lift: +100-200% on the −816% bleed if 20-30% of the bottom strategies are redirected or killed.
2. **Commission S2 walk-forward on CRYPTO ml_enhanced top candidates** (INJUSDT, DYDXUSDT, RENDERUSDT, BNBUSDT 15m variants) — these are the only strategies anywhere in the repo with Wilson LB > 50% (INJ W95 = 0.782, DYDX = 0.805).
3. **EQUITY has under-coverage** — only 53 strategies / 362 trades across US stocks. Room to grow without crowding. Kimi's batch fits here.
4. **Hold ETF work** — aggregate is flat and intermarket-flow-scout's recent edge was a streak. Wait 30d for more data before deciding.
5. **COMMODITY and BOND are data deserts** — less than 300 trades total. Not actionable until we get 100+ more resolved per class.

## Reconciliation with earlier reports

- **V3 outperformer analysis** (shipped 10 min ago as `5d5bba2c0`) said "no strategy outright outperforms" — confirmed. Even the top per-asset-class strategies here have small n or concentrated symbol exposure.
- **`st_fear_greed_contrarian` mystery resolved**: dashboard showed WR 57.1% n=718 yesterday but TRUE is WR 34.2% n=845 per the V3 re-run. It doesn't show in today's per-asset-class top-3 because the aggregate is net losing. Retirement (commit `9b586f5fe`) was correct.
- **Baseline doc** (shipped as `32931c188`) showed it at WR 57.1%, which is now known to be stale. Update pending.

---

## Review feedback — Cursor agent (2026-04-19)

1. **Aggregation semantics:** “Total realized PnL” across strategies is useful for *ranking* but can double-count overlapping books. Where possible, add a footnote whether PnL is **sum of strategy rows** vs **portfolio-compounded** — readers confuse the two when comparing to V3 / `closed_picks` aggregates.
2. **FOREX −816% vs extensive doc:** The extensive summary isolates much of the bleed to **`kimi_signal_tracking/default`**. Treat **retire-the-tail** and **block-one-combo** as separate decisions; confirm in SQL/dashboard before a blanket “stop all forex.”
3. **INJ / 100% WR:** Agree with S2 walk-forward. Add **per-symbol max exposure** in any promotion memo — concentration risk is the hidden failure mode when Wilson LB looks great on one alt.
4. **Cross-links:** Pair this snapshot with [STRATEGY_DISCOVERY_PROTOCOL.md](STRATEGY_DISCOVERY_PROTOCOL.md) (novelty + correlation pruning) and [OUTPERFORMER_ANALYSIS_2026_04_19.md](OUTPERFORMER_ANALYSIS_2026_04_19.md) so “outperform” claims stay definition-aligned.
5. **Baby / yfinance research:** Recent `baby_strategies` batches are **not** substitutes for dashboard realized stats — cite `compare_to_audit_baselines.py` / discovery protocol when mixing the two streams.

## Review feedback — Kimi Code CLI (2026-04-19)

1. **Loss-driver decomposition required before any retirement decision.** The FOREX −816% bleed is driven by **one combo** (`kimi_signal_tracking/default`). Retiring the entire asset class would throw away `forex_rsi2_mean_reversion` (+23.2%, n=138, WR 52.9%). Always run `scripts/loss_driver_analyzer.py --asset-class <CLASS>` before class-level kill memos.
2. **Crypto aggregate +108% masks a −722% bleeder.** `quan_engine_scalp` at 4,316 trades / 29.9% WR / −722% PnL is the repo's largest single loss source. Its MATICUSDT slice is 0/913 (deterministic loss). See [LOSS_DRIVER_ANALYSIS_2026_04_19.md](LOSS_DRIVER_ANALYSIS_2026_04_19.md).
3. **Add deterministic-loss exception to kill criteria.** Any strategy-symbol pair with n ≥ 20 and WR = 0% should bypass rehab and go straight to `BLOCKED_STRATEGY_SYMBOL_PAIRS`. This is not noise — it's structural mismatch (MATIC pattern).
4. **Equity top-3 has config drift.** `fast_stocks_competition/Breakout Momentum` (0% WR, −16%) vs `stocks_competition/Breakout Momentum` (53.2% WR, +49.7%) on identical strategy name suggests parameter or data-source divergence. Before promoting equity strategies, audit for name collisions.
5. **Correlation guard mandate.** Before any S4 promotion (per `STRATEGY_FACTORY_V1_PROPOSAL.md`), run `scripts/strategy_correlation_guard.py --candidate <strategy> --threshold 0.30`. This prevents rehab from accidentally cloning existing factor exposure.
