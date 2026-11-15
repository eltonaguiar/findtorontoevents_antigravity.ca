# PLAN.md — Crypto Strategy Forensic Audit & Proof Experiments

**Date:** 2026-11-15
**Asset class:** CRYPTO
**Worktree:** WIRED_IN/2026-11-15_0700_scratch-hippodraco/Plan/crypto
**Status:** Draft — ready for execution

---

## 1. HYPOTHESIS

**Primary hypothesis:** Mean-reversion on funding-rate extremes with momentum-on-convergence filter (combining hypotheses (a) and (b) from the mission).

When 8-hour perpetual funding rate is deeply negative (< -0.05%), shorts are overleveraged and a short squeeze is statistically likely → LONG. When funding is deeply positive (> +0.05%), longs are overleveraged → SHORT. **Crucial filter:** only enter when funding is simultaneously *converging toward zero* (i.e., the rate of change of funding has the opposite sign of the funding level). This avoids catching a falling knife in a strongly trending market where funding stays extreme for extended periods. Exit when funding crosses zero (mean reversion complete) or TP/SL is hit.

**Secondary hypothesis:** Market-neutral pairs trading on highly correlated pairs (BTC/ETH primary, ETH/SOL secondary). When the BTC/ETH price ratio diverges >2σ from its 24-hour rolling mean, long the underperformer and short the outperformer; exit when the ratio mean-reverts to within 0.5σ. This removes directional beta exposure — the dominant source of CRYPTO's negative expectancy.

**Rationale:** CRYPTO has n=3,705 resolved picks but WR=35.87%, PF=0.9196, verdict=NOT_READY per `audit_dashboard/data/money_ready_verdict.json:1-14`. The expectancy is -0.058445 (adj_win=0.038771, adj_loss=0.112822, slippage=15bps) — **genuine negative expectancy, not a data problem**. Gates failing: WR (≥50%), PF (≥1.5), DSR, expectancy (>0), MDD (≤20%), CVaR, bootstrap CI (>0). Gates passing: n, PBO, SPA, single_source, recency, FDR, walk-forward. The existing 112+ crypto strategies in `alpha_engine/crypto_strategies.py` are overwhelmingly long-only momentum/breakout on daily timeframes with ATR-based TP/SL that get stop-hunted by crypto wicks (79/89 losses were SL_HIT per the code comment at line 137). None incorporate funding-rate mean reversion as the primary entry trigger, none use intrabar TP-before-SL resolution, and none run market-neutral pairs. This plan fills that gap.

---

## 2. GAP FILLED

**Inventory row citation:** No `00_inventory.csv` exists in the repo (searched `**/00_inventory*` and `**/*inventory*.csv` — no match). The canonical implementation file is `alpha_engine/crypto_strategies.py`, which contains strategies 1-23 inline plus waves 4-10d delegated to separate modules (quant, event, statistical, pattern, cyclical, cerebrus, untapped, market_microstructure, basis, orderbook, tradingview waves). The gap: **none of these strategies passed all §6 gates** — per `money_ready_verdict.json` CRYPTO class:

| Gate | Threshold | CRYPTO actual | Pass? |
|------|-----------|---------------|-------|
| n (sample size) | ≥ 100 | 3,705 | PASS |
| WR | ≥ 50% | 35.87% | FAIL |
| PF | ≥ 1.5 | 0.9196 | FAIL |
| DSR | ≥ 0.95 | 0.0 | FAIL |
| Expectancy (net of slippage) | > 0 | -0.058445 | FAIL |
| MDD | ≤ 20% | 100.09% | FAIL |
| CVaR 95% | pass threshold | -95.81% | FAIL |
| Bootstrap CI lower | > 0 | -0.0508 | FAIL |
| PBO | ≤ 0.55 | 0.0 | PASS |
| SPA | p ≤ 0.10 | 0.0 | PASS |

Source concentration is extreme: `top_source="UNKNOWN"`, `top_source_share=0.9966`. Top symbol BTC-USD is only 10.66% of picks. This plan fills the gap by specifying a single pre-registered crypto strategy (funding-rate mean reversion + pairs overlay) with exact parameters, exact gates, exact pass criteria, and intrabar TP-before-SL resolution.

---

## 3. METHOD

### 3.1 Strategy A — Funding-Rate Mean Reversion with Convergence Filter (Primary)

**Direction:** LONG and SHORT (directional, but filtered by convergence momentum).

**Universe:** BTC-USD, ETH-USD, SOL-USD, ADA-USD, DOT-USD, AVAX-USD, LINK-USD (7 symbols).

**Data:** 1-hour OHLCV + 8-hour funding rate from Binance perpetual futures.

**Entry rules (evaluated at each 1h close):**

1. **Funding extreme trigger:**
   - LONG: 8h funding rate < -0.05% (shorts overleveraged, squeeze imminent)
   - SHORT: 8h funding rate > +0.05% (longs overleveraged, squeeze imminent)
   - Funding rate fetched from Binance `/fapi/v1/premiumIndex` (`lastFundingRate` field), failover mirrors `fapi1.binance.com`, `fapi2.binance.com`.

2. **Convergence momentum filter (the key differentiator):**
   - Compute funding_rate_t and funding_rate_t-1 (previous 8h funding print).
   - LONG additionally requires: funding_rate_t > funding_rate_t-1 (funding rising toward zero from negative)
   - SHORT additionally requires: funding_rate_t < funding_rate_t-1 (funding falling toward zero from positive)
   - Rationale: prevents entering when funding is extreme and *diverging further* (strong trend, squeeze not yet imminent).

3. **Volatility regime gate:** ATR(14)/close < 8% on the 1h timeframe (skip extreme volatility regimes where stops get wick-hunted).

4. **Entry price:** 1h close price of the trigger bar.

5. **Max 1 position per symbol; max 3 concurrent positions across universe** (rank by |funding_rate| descending — most extreme first when capacity-constrained).

**Exit rules (evaluated at each 1h close, intrabar TP-before-SL resolution per Section 5):**

1. **Take-profit exit:** price hits TP level → exit at TP.
2. **Stop-loss exit:** price hits SL level → exit at SL.
3. **Funding-zero exit:** funding rate crosses zero (mean reversion complete) → exit at next 1h close, even if TP/SL not hit.
4. **Max hold:** 48 hours (48 1h bars) → time exit at close regardless.
5. **Exit price:** the price at which TP/SL/funding-zero/time is triggered (intrabar-resolved per Section 5).

### 3.2 Strategy B — BTC/ETH Pairs Trading (Market-Neutral Overlay)

**Universe pair:** BTC-USD / ETH-USD (primary), ETH-USD / SOL-USD (secondary).

**Entry rules (evaluated at each 1h close):**

1. Compute ratio R = price(BTC) / price(ETH).
2. Compute rolling mean μ(24h) and rolling std σ(24h) of R on 1h data.
3. Z-score z = (R - μ) / σ.
4. LONG ETH / SHORT BTC when z > +2.0 (BTC expensive relative to ETH → mean reversion: BTC down, ETH up).
5. SHORT ETH / LONG BTC when z < -2.0 (ETH expensive relative to BTC).
6. Entry at 1h close of trigger bar; equal notional on both legs.

**Exit rules:**

1. |z| < 0.5 → mean reversion complete → exit both legs.
2. |z| > 3.5 → stop-loss (breakdown, regime change) → exit both legs.
3. Max hold: 24 hours → time exit.

### 3.3 Position Sizing

| Parameter | Value |
|-----------|-------|
| Base size (Strategy A) | 2% of portfolio equity per symbol |
| Max concurrent positions (A) | 3 (6% max gross exposure) |
| Per-symbol cap | 1 position |
| Base size (Strategy B) | 1% per leg (2% gross notional per pair) |
| Max concurrent pairs (B) | 1 pair |
| Leverage | None (spot, 1x) |
| Rebalance | At 1h close on signal |
| Ranking | By |funding_rate| descending (A) or |z| descending (B) |

### 3.4 Stop-Loss / Take-Profit (exact parameters)

| Parameter | Value | Range for grid search |
|-----------|-------|----------------------|
| Stop-loss (A) | -2.5% from entry | 2% - 4% |
| Take-profit (A) | +5.0% from entry | 3% - 8% |
| Stop-loss (B) | |z| > 3.5 | fixed |
| Take-profit (B) | |z| < 0.5 | fixed |
| Funding threshold (A) | |fr| > 0.05% | -0.05% to +0.05% |
| Lookback (A funding history) | 3 prints (24h) | 2-6 prints |
| ATR period (regime gate) | 14 | fixed |
| Max hold (A) | 48 bars | 24-96 bars |
| Max hold (B) | 24 bars | 12-48 bars |

**R:R ratio (A):** 2.0 (5% TP / 2.5% SL).
**Net-of-cost R:R:** After 30bps round-trip cost, net TP = 4.7%, net SL = -2.8%, net R:R ≈ 1.68.

---

## 4. DATA SOURCE

**Primary:** ccxt → Binance (spot OHLCV + perpetual funding rate).
- 1h OHLCV: `fetch_ohlcv(symbol, '1h', limit=500)` → ≥180 days of 1h bars (mission-critical: current backfill is only ~30 days, must extend to ≥180 days).
- 8h funding rate: `fetch_funding_rate_history(symbol)` from Binance `/fapi/v1/fundingRate`.
- Failover: KuCoin, CryptoCompare.

**Secondary (cross-validation):** `audit_dashboard/data/dashboard_data.json` — existing dashboard data containing closed CRYPTO picks (n=3,705 intrabar) for comparing live-pick stats vs backtest stats.

**Tertiary (cost model):** `tools/data/transaction_costs.json` — CRYPTO cost_bps=30 (0.30% round-trip).

**Not used:** yfinance (insufficient 1h crypto history depth), existing `dashboard_data.json` alone (lacks funding rate and 1-minute intrabar resolution).

---

## 5. TIMEFRAME

**1-hour** — crypto intrabar resolution per mission requirement. All indicators computed on 1h bars. Entry/exit evaluated at 1h close.

**Intrabar TP-before-SL resolution (CRITICAL):**

The repo found that 26.4% of TP_HITs actually hit SL first on intrabar replay (`tools/reresolve_intrabar.py`, mission context). This plan addresses it as follows:

1. **Primary:** Replay each candidate trade at **1-minute resolution** using ccxt `fetch_ohlcv(symbol, '1m')` for the holding window. Determine the *actual* first touch: if TP touched before SL → TP_HIT (win); if SL touched before TP → SL_HIT (loss); if both touched in the same 1-minute bar → flag as ambiguous, resolve conservatively to SL (per `reresolve_intrabar.py` v2 spec §7) but flag `ambiguous=True`.

2. **Fallback:** If 1-minute data unavailable, use **5-minute** resolution. Same first-touch logic.

3. **Last resort:** 1-hour bar with conservative SL-first tie-break (current repo default), but flag `ambiguous=True` and exclude ambiguous bars from PF/WR headline numbers (report them separately).

4. **Implementation:** Extend `tools/reresolve_intrabar.py` to accept a `--resolution 1m` flag and to write intrabar-resolved status to parallel columns (never overwrite canonical `trading_picks.status`/`pnl_pct`).

5. **All proof tests (Section 10) use intrabar-resolved results only.** Daily-resolution WR/PF are reported for reference but are not promotable.

---

## 6. UNIVERSE

| # | Symbol | Role |
|---|--------|------|
| 1 | BTC-USD | Strategy A + Strategy B (leg 1) |
| 2 | ETH-USD | Strategy A + Strategy B (leg 2) |
| 3 | SOL-USD | Strategy A |
| 4 | ADA-USD | Strategy A |
| 5 | DOT-USD | Strategy A |
| 6 | AVAX-USD | Strategy A |
| 7 | LINK-USD | Strategy A |

Pairs: (BTC-USD, ETH-USD) primary; (ETH-USD, SOL-USD) secondary.

No substitutions without documented reason. Universe fixed at plan registration; changes require re-pre-registration.

---

## 7. PARAMETER RANGES (grid search for optimization)

| Parameter | Range | Step | Default |
|-----------|-------|------|---------|
| Funding rate threshold (long) | -0.05% to -0.01% | 0.01% | -0.05% |
| Funding rate threshold (short) | +0.01% to +0.05% | 0.01% | +0.05% |
| Convergence lookback (prints) | 2, 3, 4, 5, 6 | 1 | 3 |
| Position size | 1%, 2%, 3%, 5% | varies | 2% |
| Stop-loss | 2%, 2.5%, 3%, 3.5%, 4% | 0.5% | 2.5% |
| Take-profit | 3%, 4%, 5%, 6%, 7%, 8% | 1% | 5% |
| ATR regime gate max | 5%, 6%, 7%, 8%, 10% | varies | 8% |
| Max hold (hours) | 24, 36, 48, 72, 96 | 12 | 48 |
| Pairs Z-score entry | 1.5, 2.0, 2.5, 3.0 | 0.5 | 2.0 |
| Pairs Z-score exit | 0.25, 0.5, 0.75, 1.0 | 0.25 | 0.5 |
| Pairs Z-score stop | 3.0, 3.5, 4.0, 5.0 | 0.5 | 3.5 |

**Grid size (A):** 5 × 5 × 5 × 5 × 5 × 5 × 5 × 5 = 390,625 combinations — feasible for 1h data on 7 symbols over ≥180 days (~4,320 bars per symbol).

**Optimization objective:** maximize PF subject to WR ≥ 50%, MDD ≤ 20%, n ≥ 100, bootstrap CI lower bound > 0, net of 30bps round-trip cost.

---

## 8. COST MODEL

**Round-trip cost: 30 bps (0.30%)** per trade, from `tools/data/transaction_costs.json`:
- CRYPTO: cost_bps=30, cost_pct=0.30
- Note: "Binance/KuCoin spot taker fee ~7bp each side + avg slippage on top 200 coins"

All backtest returns computed **net of costs**: each trade's PnL reduced by 30 bps round-trip (15bps entry + 15bps exit, or equivalent).

**Slippage:** 15 bps per `alpha_engine/money_ready_verdict.py` CRYPTO expectancy block (`slippage_bps: 15.0`).

**Net expectancy gate:** adj_win × WR − adj_loss × (1−WR) > 0 after per-class slippage (per `money_ready_verdict.py` expectancy logic). Current CRYPTO expectancy is -0.058445 — must cross above 0.

---

## 9. BENCHMARK

**BTC-USD total return**, 1-hour resolution, same ≥180-day window.

- Benchmark return computed per trade window: buy BTC-USD at entry 1h close, sell at exit 1h close.
- Paired bootstrap: mean(trade_return − benchmark_return) over (trade, benchmark) pairs, 10,000 resamples, pass requires frac_positive ≥ 0.95 and CI lower bound > 0.
- Random-entry Monte Carlo: same-asset null with window-matched nulls, 10,000 permutations, percentile ≥ 0.90 indicates timing edge.
- BTC-USD chosen because it is the dominant crypto market (top_symbol=BTCUSDT, 10.66% share) and the relevant buy-and-hold benchmark per charter (BTC for CRYPTO).

---

## 10. PROOF TESTS (§6 Gates)

The following gates must ALL pass for the strategy to be promoted. Each maps to `alpha_engine/money_ready_verdict.py` gate logic.

| # | Gate | Threshold | Implementation | Pass/Fail |
|---|------|-----------|----------------|-----------|
| 1 | Sample size n | n ≥ 100 closed clean picks | Count of completed trades (WON+LOST, exclude FLAT/active) | |
| 2 | Tier metrics (PF/WR/MDD) | PF ≥ 1.5, WR ≥ 50%, MDD ≤ 20% | PF = gross_wins/gross_losses; WR = wins/(wins+losses); MDD = peak-to-trough cumulative net PnL | |
| 3 | DSR (Deflated Sharpe Ratio) | DSR ≥ 0.95 with nb_trials correction | `alpha_engine/deflated_sharpe.py` with nb_trials = grid combinations tested | |
| 4 | SPA (White's Reality Check) | family-wise p ≤ 0.10 | `tools/whites_reality_check.py` via `money_ready_verdict.py:_spa_gate`, MIN_N_STRATEGY=20 | |
| 5 | PBO (Probability of Backtest Overfit) | PBO ≤ 0.55 | `tools/pbo_cscv.py` via `money_ready_verdict.py:_pbo_gate`, requires ≥ 5 strategies (parameter variants) | |
| 6 | Symbol/source concentration | top symbol ≤ 60%, top source ≤ 40% | `money_ready_verdict.py:_verdict` concentration caps | |
| 7 | Net-of-slippage expectancy | adj_win × WR − adj_loss × (1−WR) > 0 | `money_ready_verdict.py` expectancy with CRYPTO slippage 15 bps | |
| 8 | Bootstrap CI | 95% CI lower bound > 0 | `alpha_engine/benchmark_closed_ledger.py:paired_bootstrap`, 10,000 resamples | |
| 9 | Walk-forward OOS | OOS WR within 10pp of IS, OOS PF > 1.5 | `alpha_engine/walkforward_validator.py`, 4 overlapping sleeves, train/validate/test split | |
| 10 | Monte Carlo (random entry) | percentile ≥ 0.90 | `alpha_engine/benchmark_closed_ledger.py:random_entry_mc`, 10,000 permutations, window-matched per-symbol nulls | |
| 11 | Regime split | PF ≥ 1.2 in both bull and bear sub-periods | Split data at median BTC 200-SMA or VIX-equivalent; test each regime independently | |
| 12 | Shuffle control | Sharpe of shuffled returns < observed Sharpe | Shuffle 1h returns 1,000×, compare observed Sharpe to null | |
| 13 | Pre-registered forward test | n ≥ 30 forward trades, PF ≥ 1.2 | Out-of-sample paper forward test after grid frozen; no parameter changes after seeing forward data | |
| 14 | Reproducibility | Same seed, same code, same data → identical results | Fixed random seed (42), deterministic parameter grid, version-controlled code | |
| 15 | Intrabar resolution | All TP_HIT/SL_HIT resolved at 1m/5m first-touch | `tools/reresolve_intrabar.py --resolution 1m`; ambiguous flags reported separately | |

**Promotion rule:** All 15 gates must pass simultaneously on both (a) the rolling-90d window and (b) the frozen walk-forward window. Intrabar-resolved results are the authoritative source. Single-window passes are not promotable.

**Current CRYPTO baseline (to beat):**
- WR 35.87% → target ≥ 50%
- PF 0.9196 → target ≥ 1.5
- Expectancy -0.058445 → target > 0
- MDD 100.09% → target ≤ 20%
- Bootstrap CI [-0.0508, -0.0448] → target lower bound > 0
- Source concentration 99.66% UNKNOWN → target top source ≤ 40%

---

## 11. EXPECTED OUTCOME

**"Proven" = T2 Tier-2 floor cleared AND all §6 gates pass:**

| Metric | T2 Floor | "Proven" Target |
|--------|----------|-----------------|
| PF | ≥ 1.5 | ≥ 1.5 |
| WR | ≥ 50% | ≥ 50% |
| MDD | ≤ 20% | ≤ 20% |
| n | ≥ 100 | ≥ 100 |
| Sharpe | ≥ 1.0 | ≥ 1.0 |
| DSR | ≥ 0.95 | ≥ 0.95 |
| Bootstrap CI lower | > 0 | > 0 |
| Net expectancy | > 0 | > 0 |

**If proven:** Strategy added to `alpha_engine/data/anti_overfit_registry.json` as validated, promoted to OOS_READY per class state machine (BLOCKED → REHAB → OOS_READY → SHADOW → LIVE_ELIGIBLE), sized at 2% per position max (Strategy A) / 1% per leg (Strategy B).

**If not proven:** Document failure in `updates/` directory per AGENTS.md "Document Every Fix" rule, classify strategy as Below Tier 3 per charter, do not size real capital.

---

## 12. EXECUTION CHECKLIST

- [ ] Create backtest script: `tools/crypto_funding_mean_reversion_backtest.py` implementing Sections 3-5 exactly
- [ ] Extend `tools/reresolve_intrabar.py` with `--resolution 1m` flag and first-touch TP-before-SL logic
- [ ] Fetch ≥180 days of 1h OHLCV + funding rates for all 7 symbols from Binance (ccxt)
- [ ] Run grid search (Section 7) on 7-symbol universe
- [ ] Run all 15 §6 gates (Section 10) on intrabar-resolved results
- [ ] Document results in `updates/YYYY-MM-DD-crypto-funding-mean-reversion-backtest.md` per AGENTS.md "Document Every Fix" rule
- [ ] If all gates pass: register in `alpha_engine/data/anti_overfit_registry.json`, wire into `production_scanner.py`
- [ ] If any gate fails: document failure, do not promote
