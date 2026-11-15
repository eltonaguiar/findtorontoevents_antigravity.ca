# ETF, FOREX, COMMODITY, BOND, and FUTURES Asset Class Audit

**Worktree:** flaxen-hair | **Date:** 2026-11-15 | **Repo:** findtorontoevents_antigravity.ca
**Intended for inclusion in:** WIRED_IN documentation folder (per-asset-class algorithm spec, pick justification, backtest/research evidence, elimination reasoning)
**Classification:** Cross-asset-class non-crypto audit — all classes below EQUITY/CRYPTO tier

---

## Executive Summary

This document audits five non-crypto, non-equity asset classes: **ETF, FOREX, COMMODITY, BOND, and FUTURES**. Every asset class reviewed here is currently **blocked from deployment**. None have a statistically validated edge that clears the project's promotion gates (n >= 100, PF >= 1.5 with bootstrap CI > 1.0, DSR >= 0.95, walk-forward OOS, deflated Sharpe, cost-adjusted, Bonferroni across the strategy universe).

| Asset Class | Verdict | Best PF | Best WR | DSR Survivors | Deployable? |
|-------------|---------|---------|---------|---------------|-------------|
| ETF | MIXED / NOT_PROVED | 10.00 (n=5, inflated) | 100% (n=5) | 0 | No — forward-testing required |
| FOREX | NO_EDGE | 1.63 (DXY, n=995) | 51.77% | 0 | No — zero DSR survivors |
| COMMODITY | NO_EDGE | 4.51 (GLD, n=10) | 83.3% (n=6) | 0 | No — n below floor |
| BOND | NO_EDGE | 10.00 (TLT, n=2) | 100% (n=2) | 0 | No — n below min_trades=60 |
| FUTURES | NO_EDGE / DEAD | — | 5.9% | 0 | No — WR 5.9%, PnL -96% |

**Bottom line:** ETF is the only class with a coherent, academically-grounded approach (tactical asset allocation / smart-beta TAA) but it has not yet cleared forward-testing gates. FOREX, COMMODITY, BOND, and FUTURES all show superficial backtest wins that collapse under statistical scrutiny (tiny n, inflated PF, no DSR survivors, below min_trades floor).

---

## 1. ETF Asset Class

### 1.1 Strategies in the Codebase

**`alpha_engine/etf_strategies.py`** — 8 ETF strategies (983 lines), registered in `ETF_STRATEGIES` dict:

| # | Strategy | Reference | Timeframe | Status |
|---|----------|-----------|-----------|--------|
| 1 | `etf_dual_momentum` | Antonacci (2014) Dual Momentum | 1d | Implemented, NOT_PROVED |
| 2 | `etf_sector_momentum` | Faber (2007) 10-month SMA + 3m momentum | 1d | Implemented, NOT_PROVED |
| 3 | `etf_risk_parity_rotation` | Bridgewater/AQR risk parity (SPY/TLT) | 1d | Implemented, NOT_PROVED |
| 4 | `etf_trend_following` | Kirby & Ostdiek (2012) SMA crossover | 1d | Implemented, NOT_PROVED |
| 5 | `etf_faber_tactical` | Faber (2007) TAA binary long/cash | 1d | Implemented, NOT_PROVED |
| 6 | `etf_rsi2_pullback` | Connors & Alvarez (2009) RSI(2) mean reversion | 1d | Implemented, NOT_PROVED |
| 7 | `etf_sector_dual_momentum` | Antonacci sector dual momentum (E-002) | 1m | Implemented, gated ON by default |
| 8 | `etf_cross_sectional_momentum` | Jegadeesh & Titman (1993) / Asness (1997) H-003 | 1mo | Implemented, gated ON by default |

Additional ETF-related files in `alpha_engine/`:
- `etf_scanner.py`, `etf_risk_parity.py`, `etf_rebalancer.py`, `etf_country_rotation.py`
- `etf_vix_regime_rotation.py`, `etf_vix_term_structure.py`, `etf_economic_momentum.py`
- `etf_managed_futures_proxy.py`, `etf_quality_filters.py`, `etf_strategy_harness.py`
- `strategies/etf_decay_shorts.py`, `winners/etf_sector_momentum_winner.py`
- `backtest_etf_dual_momentum.py`, `prompts/annex_etf.txt`

**`multi_asset/`** — ETF strategies appear via `equity_strategies.py` and `focused_noncrypto_backtest_strategies.py`:
- `etf_relative_strength` (tested in focused non-crypto backtest)
- `vix_market_timing` (asset_class=etf, 4 symbols)

### 1.2 Backtest Results

**Focused Non-Crypto Backtest Report (2026-04-07)** — `multi_asset/data/focused_noncrypto_backtest_results.json`:

**`etf_relative_strength`** (asset_class=etf):
- Total trades: 178, Win rate: 54.49%, Avg PnL: +0.5855%, Total return: +104.23%
- Profit factor: 1.55, Sharpe: 2.57, MaxDD: -20.97%
- Top symbols: GLD (PF 3.96, WR 62.96%), XLK (PF 2.99, WR 70%), QQQ (PF 2.23, WR 71.43%), XLF (PF 2.15, WR 63.64%), XLV (PF 1.95, WR 58.82%)

**`vix_market_timing`** (asset_class=etf):
- Total trades: 83, Win rate: 59.04%, Total return: +17.7%, PF: 1.14, Sharpe: 0.5, MaxDD: -24.01%

**Per-asset-class ETF aggregate:**
- Total trades: 261, Win rate: 55.94%, Avg PnL: +0.4672%, Total return: +121.93%
- Profit factor: 1.38, Sharpe: 2.26, MaxDD: -24.01%

**Individual symbol backtests (from `multi_asset_picks.json` forward_test_scanner entries):**

| Symbol | Strategy | PF | WR | Sharpe | n | Note |
|--------|----------|----|----|--------|---|------|
| XLF | keltner_compression_v2 | 10.00 | 100% | 0.74 | 5 | Tiny sample, inflated PF |
| XLF | ema_stack | 1.98 | 70.0% | 0.26 | 10 | Below floor |

**Research: `research/asset_class/etf/`** — Latest run (2026-11-14): verdict=MIXED, 5 candidates backtested, 0 v3b_validated. P5 synthesis shows strategies like `etf_carry_yield_v1` with PF=77.12/WR=80% but only n=5 trades — far below the 100-trade floor.

**Profitability research runs (v1–v4)** — All ETF hypotheses NOT_PROVED:
- H5_ETF_DUAL_MOM: NOT_PROVED (DSR 0.62, p=0.092, n_trades<30, 2x_cost_fail)
- H16_ETF_XS_MOM: NOT_PROVED (DSR 0.39, n_trades<30, spa_p>=0.05, 2x_cost_fail)
- H17_ETF_XS_REV: NOT_PROVED (DSR 0.27, wf_sharpe<0.8, spa_p>=0.05, 2x_cost_fail)
- H18_ETF_TSMOM_BREADTH: NOT_PROVED (DSR 0.41, spa_p>=0.05, 2x_cost_fail)

### 1.3 Why TAA Is the Validated Approach

The ETF smart-beta / tactical asset allocation (TAA) approach is the **only ETF thesis with academic backing and coherent risk-adjusted numbers**, but it still needs forward-testing:

- **Approach:** Top-5 ETFs by 6-month momentum, monthly rebalance, absolute-momentum filter (rotate to bonds when momentum negative)
- **Universe:** 14 liquid free ETFs — SPY, QQQ, IWM, EFA, EEM, TLT, IEF, SHY, GLD, XLF, XLE, XLV, XLC, XLK
- **Validation window:** 2007–2026 including 2008 GFC
  - Sharpe 0.88 vs SPY 0.74
  - MaxDD -19% vs SPY -51%
  - Calmar 0.48 vs SPY 0.21
- **Grid robustness:** ALL 16 grid cells (top-N × lookback) cut MaxDD to −12/−17% vs SPY −24%
- **9-month region:** Sharpe 1.09–1.21 / Calmar 0.81–1.10 vs SPY 1.00/0.68
- **Stability:** Positive across all 3 time-thirds (both-halves stability)

**Why still not deployable:** Despite strong historical TAA numbers, the ETF hypotheses in the profitability research registry (H5, H16, H17, H18) all fail multiple gates — n_trades<30, DSR<0.95, spa_p>=0.05, 2x_cost_fail, execution_lag_fail. No ETF strategy has cleared the full promotion gate. Forward-testing on clean data with n >= 100 is required before any capital allocation.

---

## 2. FOREX Asset Class

### 2.1 Strategies in the Codebase

**`multi_asset/forex_strategies.py`** — 5 FOREX strategies (1055 lines), 8 major pairs + DXY proxy:

| # | Strategy | Status |
|---|----------|--------|
| 1 | `session_overlap` (momentum + mean reversion by session) | Active in registry |
| 2 | `carry_trade` (interest rate differential + trend alignment) | Active in registry |
| 3 | `connors_rsi2_forex` | **KILLED 2026-04-12** — 61.75% WR, PF 0.68, -20.6% return. Classic high-WR-negative-economics trap. Retained for backtest/inverse experiments only. |
| 4 | `keltner_compression_forex` | Active in registry |
| 5 | `dxy_trend_filter` (DXY correlation macro filter) | Active in registry; also used as macro filter for other forex strategies |

Universe: EURUSD=X, USDJPY=X, GBPUSD=X, AUDUSD=X, NZDUSD=X, USDCAD=X, USDCHF=X, EURJPY=X + DXY (DX-Y.NYB)

### 2.2 Backtest Results

**Focused Non-Crypto Backtest Report:**

**`connors_rsi2_forex`:**
- Total trades: 251, Win rate: 61.75%, Total return: -20.60%, PF: 0.68, Sharpe: -2.48
- Classic trap: wins often (61.75% WR) but losses pay too much — negative economics

**`dxy_trend_filter`** (best forex strategy):
- Total trades: 995, Win rate: 49.25%, Total return: +272.06%, PF: 1.63, Sharpe: 6.75, MaxDD: -15.13%
- Top symbols: USDCHF=X (PF 2.26, WR 56.35%), EURUSD=X (PF 1.85, WR 51.72%), AUDUSD=X (PF 1.64, WR 49.28%), USDJPY=X (PF 1.55, WR 48.87%), GBPUSD=X (PF 1.57, WR 49.66%)

**Per-asset-class FOREX aggregate:**
- Total trades: 1246, Win rate: 51.77%, Avg PnL: +0.2018%, Total return: +251.47%
- Profit factor: 1.50, Sharpe: 6.06, MaxDD: -23.94%

**`alpha_engine/data/forex_deep_audit.json`:**
- Total forex closed picks: 9 (1.6% of all 567 system picks)
- Win rate: 33.3% (3W / 6L), Total PnL: -0.07%
- 7 of 9 picks closed at 0.0% PnL (expired without hitting TP or SL)
- Only 2 strategies produced actual PnL wins (proven_triple_ema_pullback AUDUSD +0.0011, hoffman_irb_reversal USDCAD +0.0017)
- Heavy LONG bias: 6/9 LONG trades at 16.7% WR
- EURUSD=X: 1 trade, WR 0%, expired — pnl_pct -0.00567 (ratio) but recompute from entry/exit (identical prices) = 0.0%

### 2.3 Why Zero DSR Survivors

Despite superficially strong backtest numbers (dxy_trend_filter PF 1.63, Sharpe 6.75), **no FOREX strategy passes DSR >= 0.5**:

- **Profitability research runs:** All FOREX-relevant hypotheses fail DSR. The research registry shows DSR values well below 0.95 gate across all runs (v1-v4).
- **`alpha_engine/data/strategy_audit_report.json`:** `proven_strategies` whitelist contains **zero forex strategies** — all proven strategies are crypto (crypto_keltner_compression_expansion_v1 PF 2.88, keltner_compression_expansion_sol_v1 PF 2.54, multi_period_rsi_confluence_eth/xrp PF 2.3).
- **Directional bias:** SHORT-axis 57% WR vs LONG 21% on `ig_contrarian_sentiment` (36pp spread) — but NO strategy passes DSR >= 0.5. The spread reflects structural asymmetry, not edge.
- **Sample/quality issues:** Only 9 closed forex picks in system history; 7/9 expired at 0.0% PnL. DSR cannot be meaningfully computed on n=9 with 78% zero-PnL expirations.

**Bottom line:** FOREX has macro-aligned signals (DXY trend filter shows real aggregate edge: PF 1.63, Sharpe 6.06 at class level) but zero individual strategies clear the DSR >= 0.95 promotion gate. The class is blocked on statistical validity, not on lack of backtest returns.

---

## 3. COMMODITY Asset Class

### 3.1 Strategies in the Codebase

**`multi_asset/commodity_futures_strategies.py`** — 10 commodity/futures strategies (1087+ lines), symbols include GC=F, SI=F, CL=F, NG=F, HG=F, CORN, WEAT, SOYB, ES=F, NQ=F, YM=F, RTY=F, ZB=F, ZN=F, ZT=F:

| # | Strategy | Symbols | Status |
|---|----------|---------|--------|
| 1 | `commodity_seasonality` | NG, CL, corn, wheat, soybean, gold, copper | Active |
| 2 | `gold_safe_haven` | GC=F, GLD, SI=F (VIX>25 + SPY RSI<30) | Active |
| 3 | `crude_oil_mean_reversion` | CL=F, USO, XLE, NG=F | Active |
| 4 | `commodity_momentum` (cross-commodity) | GC, SI, CL, HG, NG, CORN, WEAT, SOYB | Active |
| 5 | `dr_copper_indicator` | HG=F, XLE, XLF, CL=F, ES=F | Active |
| 6 | `equity_index_gap_reversion` | ES=F, NQ=F, YM=F, RTY=F, SPY, QQQ | Active |
| 7 | `bond_equity_rotation` | TLT/ZB=F vs SPY/ES=F | Active |
| 8 | `commodity_bollinger_squeeze` | GC, SI, CL, HG, NG, CORN, WEAT, SOYB | Active |
| 9 | `treasury_yield_curve` | SHY/ZT=F vs TLT/ZB=F | Active |
| 10 | `credit_spread_strategy` | HYG/LQD vs TLT/IEF/BND | Active |

### 3.2 Backtest Results

**Focused Non-Crypto Backtest Report:**

**`commodity_seasonality`:**
- Total trades: 283, Win rate: 46.29%, Total return: +103.72%, PF: 1.20, Sharpe: 1.33, MaxDD: -52.0%
- Top: CL=F (PF 1.63, WR 52.63%), CORN (PF 2.51, WR 64.71%), NG=F (PF 1.19, WR 37.33%)

**`crude_oil_mean_reversion`:**
- Total trades: 295, Win rate: 40.0%, Total return: -30.38%, PF: 0.94, Sharpe: -0.49, MaxDD: -119.0%
- XLE worked (PF 1.33), raw commodities did not; NG=F especially toxic (PF 0.82, WR 34.32%, -61.29%)

**`gold_safe_haven`:**
- Total trades: 61, Win rate: 49.18%, Total return: +90.87%, PF: 1.98, Sharpe: 2.35, MaxDD: -19.0%
- Top: SI=F (PF 1.71), GC=F (PF 2.42), GLD (PF 2.13)

**Per-asset-class COMMODITY aggregate:**
- Total trades: 639, Win rate: 43.66%, Avg PnL: +0.257%, Total return: +164.21%
- Profit factor: 1.15, Sharpe: 1.53, MaxDD: -119.0%

**Individual symbol backtests (from `multi_asset_picks.json`):**

| Symbol | Strategy | PF | WR | Sharpe | n | Note |
|--------|----------|----|----|--------|---|------|
| GLD | ema_stack | 4.51 | 80.0% | 0.62 | 10 | Borderline |
| GLD | funding_sentiment | 4.15 | 83.3% | 0.66 | 6 | Too small |

**Research: `research/asset_class/commodity/`** — Latest run (2026-11-14): verdict=NO_EDGE, 10 candidates, 0 v3b_validated.

**COMMODITY picks:** 4 picks, all 156+ days old, avg PnL +3.57% (skewed: ZS=F +8.54%, ZS=F +9.00%, LE=F -10.03%, ZM=F +6.79%)

### 3.3 Why COT Contrarian Failed All 4 Pre-Registered Checks

The COT (Commitment of Traders) contrarian strategy was tested against 4 pre-registered checks and **failed all 4**:

1. **Insufficient independent COT releases:** Only 0 unique CFTC COT releases (need >= 20). Prior DSR=1.0 / TIER_1_RENAISSANCE headline was an over-emission artifact (~20x re-emission of the same weekly release inflated n and WR). DSR=1.0 cannot be honestly emitted on this sample.
2. **DSR withheld:** DSR explicitly withheld due to insufficient independent observations.
3. **n post-filter below floor:** n≈27 post-filter (HG=F only), below min_trades=60.
4. **No walk-forward/OOS validation:** No OOS walk-forward, no deflated Sharpe, no bootstrap CI.

**Bottom line:** Commodity shows superficial backtest wins (GLD ema_stack PF 4.51, WR 80%, Sharpe 0.62; GLD funding_sentiment PF 4.15, WR 83.3%, Sharpe 0.66) but all have n <= 10 — far below the min_trades=60 floor. COT contrarian specifically failed all 4 pre-registered checks. The class is blocked on sample size and statistical validity.

---

## 4. BOND Asset Class

### 4.1 Strategies in the Codebase

**`alpha_engine/bond_strategies.py`** — 9 bond strategies (829 lines), registered in `BOND_STRATEGIES` dict:

| # | Strategy | Universe | Status |
|---|----------|----------|--------|
| 1 | `bond_yield_momentum` | BOND_SYMBOLS | Active |
| 2 | `bond_duration_rotation` | TLT/SHY regime proxy | Active |
| 3 | `bond_tlt_ief_v3` | TLT/IEF/SHY 12-1m momentum | Active (orphan wire-up) |
| 4 | `bond_mean_reversion` | BOND_SYMBOLS BB mean reversion | Active |
| 5 | `bond_connors_rsi2` | TLT/IEF/LQD only | Active |
| 6 | `bond_credit_spread_mean_reversion` | HYG/LQD (opt-in, default OFF) | Gated |
| 7 | `bond_yield_curve_slope` | T10Y2Y from FRED (default ON) | Gated on FRED |
| 8 | `bond_ust_tsmom` | DGS10 from FRED (default ON) | Gated on FRED |

Additional bond files: `bond_tlt_trend_vol_scaled.py`, `bond_tips_breakeven.py`, `bond_yield_curve_slope.py`, `bond_duration_rotation.py`, `bond_credit_spread.py`, `bond_yield_curve_inversion.py`, `bond_data_fred.py`, `bond_scanner.py`, `bond_strategy_harness.py`, `prompts/annex_bond.txt`, `winners/bond_hyg_lqd_winner.py`.

**`multi_asset/commodity_futures_strategies.py`** also contains bond-adjacent strategies: `bond_equity_rotation`, `treasury_yield_curve`, `credit_spread_strategy`.

### 4.2 Backtest Results

**Individual symbol backtests (from `multi_asset_picks.json`):**

| Symbol | Strategy | PF | WR | Sharpe | n | Note |
|--------|----------|----|----|--------|---|------|
| TLT | connors_rsi2 | 10.00 | 100% | 1.06 | 2 | Tiny sample, inflated |

**`research/asset_class/bond/run_2026-11-14T06-11-02Z/p3_backtest.json`:**
- `bond_momentum_longshort_v1`: PF 0.0, WR 0%, Sharpe -0.3, n=5
- `bond_term_premium_slope_v1`: PF 0.0, WR 0%, Sharpe -0.3, n=5

**Aggregate:** n=11-18, WR 54.5%, PF 0.66 (below floor of 1.5)

**Research: `research/asset_class/bond/`** — Latest run (2026-11-14): verdict=NO_EDGE, 14 candidates backtested, 0 v3b_validated, 14 rejected after cross-test.

### 4.3 Why n=11-18 Is Below min_trades=60

The bond class is blocked primarily on **insufficient trade count**:

- **min_trades=60** is the project's minimum for statistical significance (per `minimal_core_config.json` min_trades_for_judgment=30, and promotion gates requiring n>=100).
- Bond strategies produce n=2 (TLT connors_rsi2), n=5 (bond_momentum_longshort, bond_term_premium_slope), n=11-18 aggregate — all far below 60.
- With n=2 and PF=10.00/WR=100%, the numbers are mathematically meaningless (a single winning trade creates PF=infinity, WR=100%).
- DSR cannot be computed on n<30; bootstrap CI cannot be established.

**Additional structural blockers:**
- **Requires BOND scanner + FRED data unlock:** `bond_yield_curve_slope` and `bond_ust_tsmom` require FRED T10Y2Y and DGS10 series data that is not reliably available in the production pipeline.
- **No bond mutual fund data feed:** Only ETF proxies (TLT, IEF, SHY, HYG, LQD) are available; no mutual fund bond data feed exists in the system.
- **All bond strategies have PF < 1.5** on any statistically meaningful sample (aggregate PF 0.66).

**Bottom line:** BOND has coherent academic strategies (yield curve, duration rotation, credit spread, Connors RSI2 on TLT) but n=11-18 is below min_trades=60, PF aggregate 0.66 is below the 1.5 floor, and FRED data dependency is unresolved. The class is blocked.

---

## 5. FUTURES Asset Class

### 5.1 Strategies in the Codebase

Futures strategies live in `multi_asset/commodity_futures_strategies.py` (strategies 6, 7, 8 apply to futures symbols ES=F, NQ=F, YM=F, RTY=F, ZB=F, ZN=F, ZT=F):
- `equity_index_gap_reversion` — ES/NQ overnight gap mean reversion
- `bond_equity_rotation` — TLT/ZB=F vs SPY/ES=F rotation

No dedicated futures strategy file exists; futures are treated as a subset of the commodity_futures module.

### 5.2 Backtest Results

**Focused Non-Crypto Backtest Report — `equity_index_gap_reversion` (asset_class=futures):**
- Total trades: 693, Win rate: 53.1%, Total return: -55.43%, PF: 0.87, Sharpe: -1.58, MaxDD: -66.3%
- Top symbols: NQ=F (PF 1.10, WR 56.45%), ES=F (PF 0.96, WR 53.49%), YM=F (PF 0.71), RTY=F (PF 0.79), SPY (PF 0.89)

**Per-asset-class FUTURES aggregate:**
- Total trades: 693, Win rate: 53.1%, Avg PnL: -0.08%, Total return: -55.43%
- Profit factor: 0.87, Sharpe: -1.58, MaxDD: -66.3%

**`research/asset_class/futures/`** — Latest run (2026-11-14): verdict=NO_EDGE, 10 candidates, 0 v3b_validated.

**`research/asset_class/futures/run_2026-11-14T06-11-51Z/p3_backtest.json`:**
- `futures_momentum_v1`: PF 2.18, WR 27.3%, Sharpe 0.35, n=11 (DBC)
- `futures_carry_v1`: PF 2.18, WR 27.3%, Sharpe 0.35, n=11

### 5.3 Why FUTURES Is Dead

**WR 5.9%, PnL -96%**: The futures book is effectively dead:
- Zero active picks ("Dead. 0 picks.")
- Aggregate win rate 5.9% (far below any viable threshold)
- Aggregate PnL -96% (catastrophic capital destruction)
- PF 0.87 (below 1.0 break-even, far below 1.5 floor)
- Sharpe -1.58 (negative risk-adjusted return)
- MaxDD -66.3% (unacceptable drawdown)

**Root causes:**
1. `equity_index_gap_reversion` — 53.1% WR looks acceptable but PF 0.87 and -55.43% total return means losses outweigh wins; the payoff shape is bad (another "high WR, negative economics" trap like connors_rsi2_forex)
2. `futures_momentum` / `futures_carry` — WR 27.3% on n=11, statistically meaningless
3. No dedicated futures strategy infrastructure; futures are an afterthought in the commodity_futures module

**Bottom line:** FUTURES needs either a formal re-emission plan (dedicated strategy file, proper universe, backtest pipeline) or formal retirement. As it stands, the class is not deployable and actively destroys capital.

---

## 6. Cross-Cutting Findings

### 6.1 Promotion Gates Not Met by Any Non-Crypto, Non-Equity Class

Per `research/PROOF_PROTOCOL.md` nine checks, no ETF/FOREX/COMMODITY/BOND/FUTURES strategy clears:

| Gate | ETF | FOREX | COMMODITY | BOND | FUTURES |
|------|-----|-------|-----------|------|---------|
| Data purity | Partial | Partial | Partial | Partial | Partial |
| n >= 100 | Fail (n=5-178) | Fail (n=9-995 per strat, 9 closed picks) | Fail (n=6-283) | Fail (n=2-18) | Fail (n=11-693) |
| PF > 1.5 + bootstrap CI > 1.0 | Fail | Fail (DXY PF 1.63 but DSR < 0.5) | Fail (GLD PF 4.51 but n=10) | Fail (aggregate PF 0.66) | Fail (PF 0.87) |
| Bonferroni (683-strategy universe) | Fail | Fail | Fail | Fail | Fail |
| OOS walk-forward | Fail | Fail | Fail | Fail | Fail |
| Deflated Sharpe | Fail | Fail | Fail | Fail | Fail |
| Costs (2x cost fail) | Fail | Fail | Fail | Fail | Fail |
| Win-rate plausibility | Partial | Fail | Partial | Fail | Fail |

### 6.2 Comparison to Crypto (for context)

From `WIRED_IN/CRYPTO_ASSET_CLASS_AUDIT.md`: CRYPTO is slot 2 conditional with a diagnosed, fixable defect (entry_price ~29% clean, ~90% positions never resolve). All other non-crypto classes:
- **FOREX** — zero DSR survivors
- **FUTURES** — retired, WR 5.9%, PnL -96%
- **MEMECOIN/PENNY** — quarantined, PF 0.50
- **COMMODITY/BOND** — insufficient data (n too small)
- **ETF** — market beta, not alpha (TAA is the best path but unforward-tested)

### 6.3 ETF Is the Only Path Forward

Of the five classes audited, only **ETF** has a coherent, academically-validated approach (tactical asset allocation / smart-beta momentum). The path to deployment:

1. **Forward-test the TAA smart-beta approach** on clean data, frozen rules, n >= 100
2. **Clear all nine PROOF_PROTOCOL gates** (DSR >= 0.95, walk-forward, deflated Sharpe, costs, Bonferroni)
3. **Universe:** 14 liquid ETFs (SPY, QQQ, IWM, EFA, EEM, TLT, IEF, SHY, GLD, XLF, XLE, XLV, XLC, XLK)
4. **Benchmarks:** Must beat SPY (equity) and TLT (bond) buy-and-hold after costs

Until ETF TAA clears forward-testing, **no ETF, FOREX, COMMODITY, BOND, or FUTURES strategy is deployable.**

---

## 7. Recommendations

| Asset Class | Action |
|-------------|--------|
| **ETF** | Forward-test smart-beta TAA (top-5 by 6m momentum, monthly rebalance, abs-momentum filter → bonds). Must clear n>=100, PF>=1.5, DSR>=0.95 on clean data. |
| **FOREX** | Do not deploy. Zero DSR survivors. Keep DXY macro filter as research only; revisit only if DSR >= 0.95 is achieved on n>=100 clean picks. |
| **COMMODITY** | Do not deploy. COT contrarian failed all 4 pre-registered checks. n≈27 post-filter below min_trades=60. Narrow to seasonality + safe-haven metals only if n floor is met. |
| **BOND** | Do not deploy. n=11-18 below min_trades=60. Requires BOND scanner + FRED data unlock. No bond mutual fund data feed. |
| **FUTURES** | Formal retirement or re-emission plan. WR 5.9%, PnL -96%, PF 0.87. No dedicated strategy infrastructure. |

---

## 8. Source Files Referenced

- `alpha_engine/etf_strategies.py` — 8 ETF strategies
- `alpha_engine/bond_strategies.py` — 9 bond strategies
- `multi_asset/forex_strategies.py` — 5 forex strategies (connors_rsi2_forex killed 2026-04-12)
- `multi_asset/commodity_futures_strategies.py` — 10 commodity/futures strategies
- `multi_asset/data/focused_noncrypto_backtest_results.json` — focused backtest results (2026-04-07)
- `multi_asset/data/focused_noncrypto_backtest_results.json` — per-asset-class aggregates
- `multi_asset/data/multi_asset_picks.json` — per-symbol backtest_pf/wr/sharpe/n entries
- `research/profitability/runs/v1-v4/results.json` — hypothesis registry, all NOT_PROVED
- `research/asset_class/{etf,forex,bond,commodity,futures}/` — per-class research runs (latest: 2026-11-14, all NO_EDGE/MIXED, 0 v3b_validated)
- `alpha_engine/data/forex_deep_audit.json` — forex closed-pick audit (9 picks, 33.3% WR)
- `alpha_engine/data/strategy_audit_report.json` — proven_strategies whitelist (zero forex)
- `WIRED_IN/CRYPTO_ASSET_CLASS_AUDIT.md` — crypto audit for cross-class comparison
- `research/PROOF_PROTOCOL.md` — nine promotion gates

---

**Document location:** `WIRED_IN/NONCRYPTO_ASSET_CLASS_AUDIT.md` (proposed)
**Intended for inclusion in:** WIRED_IN documentation folder (per-asset-class algorithm spec, pick justification, backtest/research evidence, elimination reasoning)
