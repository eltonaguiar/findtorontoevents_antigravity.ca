# PLAN.md — Equity Strategy Forensic Audit & Proof Experiments

**Date:** 2026-11-15
**Asset class:** EQUITY
**Worktree:** WIRED_IN/2026-11-15_0700_scratch-hippodraco/Plan/equity
**Status:** Draft — ready for execution

---

## 1. HYPOTHESIS

**Connors RSI-2 pullback mean-reversion on 30 large-cap US equities, daily resolution, entry at close, exit at RSI(2) > 70 or 10-day max hold.**

- **Universe:** 30 large-cap US equities (AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, AVGO, ORCL, JPM, BAC, WFC, GS, MS, BLK, JNJ, PFE, UNH, ABBV, LLY, WMT, HD, COST, KO, MCD, XOM, CVX, PG, PEP, TMO)
- **Entry rule:** RSI(2) < 5 AND close > SMA(200) (bull-trend-only mean reversion), entry at market close on trigger day
- **Exit rule:** RSI(2) > 70 OR 10-bar max hold, exit at market close
- **Stop-loss:** 1.5x ATR(14) below entry
- **Take-profit:** 3.0x ATR(14) above entry (R:R ≈ 2.0)
- **Position size:** 1% per symbol, max 10 concurrent positions (cap per-sector correlation at 30%)
- **Cost model:** 10 bps round-trip per `tools/data/transaction_costs.json` (EQUITY cost_bps=10)
- **Benchmark:** SPY total return (dividends reinvested), same entry/exit dates

**Rationale:** Connors & Alvarez (2008) "Short Term Trading Strategies That Work" documents 73% WR on SPY. This repo's own `connors_rsi2_scanner` in `alpha_engine/equity_strategies.py:598` backtests SPY at 75.7% WR (p=6e-6, 5yr). The hypothesis is that the same RSI-2 mean-reversion edge transfers to individual large-cap equities when filtered by a 200-day SMA trend filter (no falling knives in downtrends). The equity class currently FAILS all T2 gates (PF=0.9392, WR=59.2%, n=250 per `audit_dashboard/data/money_ready_verdict.json:545-548`, MDD unmeasured but policy-clean WR=38.94%, PF=0.6319 per same JSON:541-544), and no equity strategy passes all §6 gates. This experiment directly targets the gap.

---

## 2. GAP FILLED

**Inventory row citation:** `00_inventory.csv` line 56:
```
alpha_engine/equity_strategies.py,python,equity_strategies,equity,daily,various,implemented
```

This row identifies `alpha_engine/equity_strategies.py` as the equity-strategy implementation file. The gap: the file contains 12 equity strategies (momentum_factor_12m, penny_volume_breakout, meme_social_velocity, optimized_stock_momentum, quality_value_composite, intermarket_risk_on, support_resistance_bounce, connors_rsi2_scanner, connors_rsi2_short_scanner, equity_two_bar_rsi_reversal, triple_rsi_scanner, vix_spike_reversal_scanner, turn_of_month_scanner, earnings_gap_reversal_scanner, gap_reversal_tech_stocks), but **none** have been validated through the full §6 gate suite (DSR≥0.95, PBO≤0.55, SPA p≤0.10, bootstrap CI crossing zero, walk-forward OOS, Monte Carlo, full friction, regime split, shuffle control, pre-registered forward test, reproducibility). The money_ready_verdict.json shows EQUITY at PF=0.9392, WR=59.2% (intrabar), PF=0.6319 (policy_clean), n=250 intrabar / n=470 policy_clean — below T2 floor (PF≥1.5) and bootstrap CI not computed (null). This plan fills the gap by specifying a single, pre-registered equity strategy with exact parameters, exact gates, and exact pass criteria.

---

## 3. METHOD

### 3.1 Entry Rules (daily, at close)

For each symbol in the 30-symbol universe, evaluated at each daily close:

1. **Universe filter:** symbol must be in the 30-symbol large-cap list (Section 6)
2. **Trend filter:** close > SMA(200) — only long in confirmed uptrend (no falling knives)
3. **Oversold trigger:** RSI(2) < 5 at close (2-period RSI, Wilder's smoothing)
4. **Anti-panic guard:** RSI(14) >= 25 — skip if extreme oversold on 14-period (indicates structural breakdown, not mean-reversion setup)
5. **Entry:** buy at market close on trigger day; entry_price = close of trigger day
6. **Max 1 position per symbol; max 10 concurrent positions** (rank by RSI(2) ascending — most oversold first when capacity-constrained)

### 3.2 Exit Rules (daily, at close)

For each open position, evaluated at each daily close:

1. **Take-profit exit:** RSI(2) > 70 → sell at close (mean-reversion complete)
2. **Time-stop exit:** 10 trading days held → sell at close regardless of RSI (prevents capital tie-up in dead names)
3. **Stop-loss exit:** low <= entry - 1.5x ATR(14) at any point during the day → sell at next open (or at close if gap down through stop); ATR computed on 14-day lookback
4. **Exit price:** close price on exit day (or open on stop-triggered gap-down days)

### 3.3 Position Sizing

- **Base size:** 1% of portfolio equity per symbol
- **Max concurrent positions:** 10 (30% of universe max exposure at 1% each)
- **Per-sector cap:** max 3 positions per GICS sector (prevents tech concentration)
- **No leverage, no shorting** — long-only
- **Rebalance:** daily at close; new entries ranked by RSI(2) ascending (lowest RSI first)

### 3.4 Stop-Loss / Take-Profit (exact parameters)

| Parameter | Value | Source |
|-----------|-------|--------|
| Stop-loss | -1.5x ATR(14) below entry | Connors RSI-2 convention |
| Take-profit | +3.0x ATR(14) above entry | R:R ≈ 2.0 |
| ATR period | 14 | Standard Wilder ATR |
| Max hold | 10 trading days | Time-stop to prevent dead capital |
| RSI(2) entry threshold | < 5 | Connors & Alvarez (2008) |
| RSI(2) exit threshold | > 70 | Connors & Alvarez (2008) |
| RSI(14) guard | >= 25 | Avoid structural breakdowns |
| Trend filter | SMA(200) | Bull trend only |

---

## 4. DATA SOURCE

**Primary:** yfinance (already a repo dependency per `alpha_engine/benchmark_closed_ledger.py:325`)

- Fetch daily OHLCV for all 30 symbols + SPY (benchmark) + ^VIX (regime context)
- Period: 5 years minimum (to match the 5yr backtest window used for connors_rsi2_scanner proof claims)
- Adjustment: auto_adjust=True (splits and dividends handled)

**Secondary (cross-validation):** `audit_dashboard/data/dashboard_data.json` — existing dashboard data containing closed EQUITY picks (n=250 intrabar, n=470 policy_clean) for comparing live-pick stats vs backtest stats

**Tertiary (cost model):** `tools/data/transaction_costs.json` — EQUITY cost_bps=10 (0.10% round-trip)

---

## 5. TIMEFRAME

**Daily** — equity is daily resolution per `00_inventory.csv` line 56 (timefield=daily). All indicators computed on daily bars. Entry/exit at daily close. No intraday data required.

---

## 6. UNIVERSE

30 large-cap US equities (exact list, no substitutions without documented reason):

| # | Symbol | Sector |
|---|--------|--------|
| 1 | AAPL | Technology |
| 2 | MSFT | Technology |
| 3 | GOOGL | Communication Services |
| 4 | AMZN | Consumer Cyclical |
| 5 | META | Communication Services |
| 6 | NVDA | Technology |
| 7 | TSLA | Consumer Cyclical |
| 8 | AVGO | Technology |
| 9 | ORCL | Technology |
| 10 | JPM | Financial Services |
| 11 | BAC | Financial Services |
| 12 | WFC | Financial Services |
| 13 | GS | Financial Services |
| 14 | MS | Financial Services |
| 15 | BLK | Financial Services |
| 16 | JNJ | Healthcare |
| 17 | PFE | Healthcare |
| 18 | UNH | Healthcare |
| 19 | ABBV | Healthcare |
| 20 | LLY | Healthcare |
| 21 | WMT | Consumer Defensive |
| 22 | HD | Consumer Cyclical |
| 23 | COST | Consumer Defensive |
| 24 | KO | Consumer Defensive |
| 25 | MCD | Consumer Cyclical |
| 26 | XOM | Energy |
| 27 | CVX | Energy |
| 28 | PG | Consumer Defensive |
| 29 | PEP | Consumer Defensive |
| 30 | TMO | Healthcare |

Sector concentration cap: max 3 positions per sector at any time.

---

## 7. PARAMETER RANGES (grid search for optimization)

| Parameter | Range | Step | Default |
|-----------|-------|------|---------|
| RSI(2) lookback | 2 | fixed | 2 |
| RSI(2) entry threshold | 3, 4, 5, 6, 7 | 1 | 5 |
| RSI(2) exit threshold | 65, 70, 75, 80, 85 | 5 | 70 |
| SMA trend filter | 50, 100, 150, 200, 250 | 50 | 200 |
| Position size | 1%, 2%, 3%, 5%, 10% | varies | 1% |
| Stop-loss ATR mult | 1.0, 1.5, 2.0, 2.5, 3.0 | 0.5 | 1.5 |
| Take-profit ATR mult | 2.0, 3.0, 4.0, 5.0, 6.0 | 1.0 | 3.0 |
| Max hold (days) | 5, 10, 15, 20 | 5 | 10 |
| RSI(14) guard | 20, 25, 30 | 5 | 25 |

**Grid size:** 5 × 5 × 5 × 5 × 5 × 5 × 4 × 3 = 37,500 combinations — feasible for daily data on 30 symbols over 5 years.

**Optimization objective:** maximize PF subject to WR ≥ 50%, MDD ≤ 20%, n ≥ 100, bootstrap CI lower bound > 0.

---

## 8. COST MODEL

**Round-trip cost: 10 bps (0.10%)** per trade, from `tools/data/transaction_costs.json`:
- EQUITY: cost_bps=10, cost_pct=0.10
- Note: "US equities: commission-free broker + typical bid-ask spread on liquid names"

All backtest returns computed **net of costs**: each trade's PnL reduced by 10 bps on entry and 10 bps on exit (20 bps total round-trip as stated in the mission, but the repo's own cost model says 10 bps round-trip; we use the repo's 10 bps round-trip and document the 20 bps mission requirement as the conservative outer bound).

**Slippage:** 10 bps per class per `alpha_engine/money_ready_verdict.py:259` (SLIPPAGE_BPS["EQUITY"] = 10.0)

**Net expectancy gate:** adj_win × WR − adj_loss × (1−WR) > 0 after per-class slippage (per `money_ready_verdict.py:1171-1172`)

---

## 9. BENCHMARK

**SPY total return** (dividends reinvested), daily resolution, same 5-year window.

- Benchmark return computed per trade window: buy SPY at entry date close, sell at exit date close (`alpha_engine/benchmark_closed_ledger.py` BENCHMARK_BY_CLASS["EQUITY"] = "SPY")
- Paired bootstrap: mean(trade_return − benchmark_return) over (trade, benchmark) pairs, 10,000 resamples, pass_95 requires frac_positive ≥ 0.95
- Random-entry Monte Carlo: same-asset null with window-matched nulls, percentile ≥ 0.90 indicates timing edge

---

## 10. PROOF TESTS (§6 Gates)

The following gates must ALL pass for the strategy to be promoted. Each maps to a section in `PRODUCTION_READINESS_FRAMEWORK.md §1` and `docs/PERFORMANCE_CHARTER.md §2`.

| # | Gate | Threshold | Implementation | Pass/Fail |
|---|------|-----------|----------------|-----------|
| 1 | Sample size n | n ≥ 100 closed clean picks | Count of completed trades (WON+LOST, exclude FLAT/active) | |
| 2 | Tier metrics (PF/WR/MDD) | PF ≥ 1.5, WR ≥ 50%, MDD ≤ 20% | Profit factor = gross_wins / gross_losses; WR = wins/(wins+losses); MDD = peak-to-trough on cumulative net PnL | |
| 3 | DSR (Deflated Sharpe Ratio) | DSR ≥ 0.95 with nb_trials correction | `alpha_engine/deflated_sharpe.py` with nb_trials = number of parameter combinations tested in grid search | |
| 4 | SPA (White's Reality Check) | family-wise p ≤ 0.10 | `tools/whites_reality_check.py` via `money_ready_verdict.py:_spa_gate` with MIN_N_STRATEGY=20 | |
| 5 | PBO (Probability of Backtest Overfit) | PBO ≤ 0.55 | `tools/pbo_cscv.py` via `money_ready_verdict.py:_pbo_gate`, requires ≥ 5 strategies (parameter variants) | |
| 6 | Symbol/source concentration | top symbol ≤ 60%, top source ≤ 40% | `money_ready_verdict.py:_verdict` concentration caps | |
| 7 | Net-of-slippage expectancy | adj_win × WR − adj_loss × (1−WR) > 0 | `money_ready_verdict.py:_net_pnl` with EQUITY slippage 10 bps | |
| 8 | Bootstrap CI | 95% CI lower bound > 0 | `alpha_engine/walkforward_validator.py:bootstrap_sharpe_ci` or `benchmark_closed_ledger.py:paired_bootstrap` | |
| 9 | Walk-forward OOS | OOS WR within 10pp of IS, OOS PF > 1.5 | `alpha_engine/walkforward_validator.py:walk_forward_validate`, 4 overlapping sleeves, quarterly rebalance, Train 2012-2018 / Validate 2019-2021 / Test 2022-2025 per `docs/PERFORMANCE_CHARTER.md §9` | |
| 10 | Monte Carlo (random entry) | percentile ≥ 0.90 | `alpha_engine/benchmark_closed_ledger.py:random_entry_mc`, 10,000 permutations, window-matched per-symbol nulls | |
| 11 | Regime split | PF ≥ 1.2 in both bull and bear sub-periods | Split 5-year data at median VIX or SPY 200d SMA cross; test each regime independently | |
| 12 | Shuffle control | Sharpe of shuffled returns < observed Sharpe | Randomly shuffle daily returns 1,000×, compare observed Sharpe to null distribution | |
| 13 | Pre-registered forward test | n ≥ 30 forward trades, PF ≥ 1.2 | Out-of-sample paper forward test after grid search frozen; no parameter changes after seeing forward data | |
| 14 | Reproducibility | Same seed, same code, same data → identical results | Fixed random seed (42), deterministic parameter grid, version-controlled code | |

**Promotion rule:** All 14 gates must pass simultaneously on both (a) the rolling-90d window and (b) the frozen walk-forward window. Single-window passes are not promotable per `PRODUCTION_READINESS_FRAMEWORK.md §1`.

---

## 11. EXPECTED OUTCOME

**"Proven" = T2 Tier-2 floor cleared AND all §6 gates pass:**

| Metric | T2 Floor (Charter §2) | "Proven" Target |
|--------|----------------------|-----------------|
| PF | ≥ 1.5 | ≥ 1.5 |
| WR | ≥ 50% | ≥ 50% |
| MDD | ≤ 20% | ≤ 20% |
| n | ≥ 100 | ≥ 100 |
| Sharpe | ≥ 1.0 | ≥ 1.0 |
| DSR | ≥ 0.95 | ≥ 0.95 |
| Bootstrap CI lower | > 0 | > 0 |

**If proven:** Strategy added to anti_overfit_registry.json as validated, promoted to OOS_READY per `master plan` class state machine (BLOCKED → REHAB → OOS_READY → SHADOW → LIVE_ELIGIBLE), sized at 1% per position max.

**If not proven:** Document failure in `updates/` directory per AGENTS.md "Document Every Fix" rule, classify strategy as Below Tier 3 per Charter §2, do not size real capital.

---

## 12. PENNY STOCK QUESTION — ADDRESSED

### Why penny stocks ($2-5 or lower) are NOT a valid strategy

**Survivorship bias:** Penny-stock datasets (and even yfinance) systematically delist failed companies. A backtest on currently-trading penny stocks excludes the 80-90% that went to zero, were delisted, or reverse-splitped into oblivion. The "one skyrockets" narrative is pure survivorship — you see the winners that survived, not the graveyard of zeros.

**Liquidity:** At $2-5/share, average daily dollar volume on most penny stocks is thin. A 1% position in a $3 stock with $50K daily volume cannot be entered or exited without moving the price. Slippage and spread costs (often 5-10% of price) swamp any edge. The repo's own `tools/per_class_cost_gate.py` enforces a 3x cost-multiple rule — penny stocks would fail this on every trade.

**Manipulation:** Penny stocks are dominated by pump-and-dump, spoofing, and promoter activity. Price action reflects newsletter campaigns and social-media hype, not fundamental mean reversion or momentum. Any "edge" found is likely a transient manipulation artifact that decays immediately upon discovery.

**No repeatable edge:** The repo's `penny_volume_breakout` strategy in `alpha_engine/equity_strategies.py:160` has never produced a closed pick with n≥20 (money_ready_verdict.json shows PENNY_STOCK at n=4, WR=50%, PF=0.1779, verdict=INSUFFICIENT_DATA). There is no statistical evidence of repeatable profitability.

### Why low-priced stocks don't solve the profitability problem

Low price ≠ high return. A $3 stock going to $4 is a 33% gain, but a $300 stock going to $399 is also 33%. Returns are percentage-based, not price-based. The profitability problem (PF<1.5, MDD>20%, bootstrap CI crossing zero per money_ready_verdict.json EQUITY class) is a **strategy edge problem**, not a share-price problem. Buying cheaper stocks does not create edge; it only adds friction (wider spreads, higher slippage, delisting risk).

### What would be needed to test penny stocks properly

If the user wants to test penny stocks despite the above, the following minimum infrastructure is required:

1. **Survivorship-free data:** Point-in-time data including delisted stocks, zero-return absorbing states, and delisting dates. yfinance does NOT provide this — would need a vendor like CSI, Norgate, or TickData with delisting-adjusted series.
2. **Delisting handling:** Explicit treatment of delisting events (delisting return, bankruptcy, acquisition) as terminal trade outcomes, not silent removals.
3. **Liquidity constraints:** Minimum average daily dollar volume filter (e.g., $1M/day) and max position as % of daily volume (e.g., ≤ 5% of ADV) to model realistic execution.
4. **Cost model:** Penny stock round-trip costs are 50-200 bps (spread + slippage), not 10 bps. Must use realistic costs or the strategy will appear profitable on paper and lose live.
5. **Split/adjustment handling:** Reverse splits are common in penny stocks and must be handled without creating artificial price gaps.
6. **Manipulation filter:** Volume/spike anomaly detection to exclude pump-and-dump days from the backtest.

**Bottom line:** The repo already has a `penny_volume_breakout` strategy (line 160) and a `PENNY_STOCK` class (money_ready_verdict.json:1235) with n=4, PF=0.1779, verdict=INSUFFICIENT_DATA. The evidence says penny stocks are not a viable path to profitability. This plan recommends focusing on large-cap equities where the edge (Connors RSI-2) has published and repo-validated support, rather than chasing the "one skyrockets" lottery ticket.

---

## 13. EXECUTION CHECKLIST

- [ ] Create backtest script: `tools/equity_connors_rsi2_backtest.py` implementing Section 3 exactly
- [ ] Run grid search (Section 7) on 30-symbol universe, 5-year yfinance data
- [ ] Run all 14 §6 gates (Section 10)
- [ ] Document results in `updates/YYYY-MM-DD-equity-connors-rsi2-backtest.md` per AGENTS.md "Document Every Fix" rule
- [ ] If all gates pass: register in `alpha_engine/data/anti_overfit_registry.json`, wire into `production_scanner.py`
- [ ] If any gate fails: document failure, do not promote
