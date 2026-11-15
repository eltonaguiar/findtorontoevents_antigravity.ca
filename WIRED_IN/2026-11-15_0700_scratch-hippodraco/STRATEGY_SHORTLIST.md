# STRATEGY_SHORTLIST.md — findtorontoevents_antigravity.ca
Generated: 2026-11-15T08:00Z UTC  
> Template only: no numbers or profitability verdicts are implied.  
> Repeat the candidate section for each strategy and compare to no-trade/cash and relevant implementable passive alternatives.  
> Past performance and even a successful forward test do not guarantee future results.  
> Use FORWARD-SUPPORTED only after a genuinely prospective, frozen protocol passes its prespecified economic and statistical criteria.  
> A backtest-only result cannot qualify. If no candidate qualifies, say so explicitly.

---

## Summary

| Rank | Candidate / class | Verdict | Data / independent test | Net result vs benchmark / uncertainty | Main blocker / next step |
|---:|---|---|---|---|---|
| 1 | EQUITY `stocks_rsi2_pullback` | REJECT | n=78 closed picks (phase10b); n=34 closed picks (phase2) | WR 44.9% / PF 1.11 (phase10b); WR 52.94% / PF 1.522 (phase2); both below n≥100 minimum; SPY beat rate 45.53% | n < 100; median excess vs SPY -0.57%; t-stat 1.05 < 2.0 |
| 2 | BOND `bond_connors_rsi2` | REJECT | Hypothetical backtest n=201 closed (of 269) | WR 50.25%, PF 1.3383, MDD 17.79% | Hypothetical backtest, not real trades; no walk-forward folds; no cost model |
| 3 | CRYPTO `prediction_market_consensus` | REJECT | Backtest n=89; forward dashboard n=110 | Backtest WR 89.89%, PF 24.51, DSR 9.36, PBO 0.603; Forward WR 79.09%, PF 13.20 (shadow mode only) | PBO 0.603 >> 0.10 gate; pick_count=0 (not emitting live); no resolved forward trades |
| 4 | ETF `etf_rsi2_pullback` / `etf_dual_momentum` / `etf_faber_tactical` | REJECT | n=1 closed pick (QQQ, LOST at -0.01%) | WR 0%, PF 0.00 | n=1; claimed 56.1% WR/1.34 PF does not match ground truth; 134 TIME_EXIT with forced pnl=0 |
| 5 | FOREX `multi_asset_copytrader` | REJECT | n=176 closed picks | WR 13.64% (of all n), PF 0.6596 | MDD 82%; walk-forward OOS PF 0.4829; policy_frozen=true |
| 6 | FUTURES `multi_asset_copytrader` | REJECT | n=31 closed picks | WR 0%, all $0 PnL | All force-closed toxic; stale 246 days since last pick |
| 7 | BOND `bond_duration_rotation` | REJECT | Hypothetical backtest n=279 periods | WR 54.48%, PF 1.3439, MDD 27.28% | Hypothetical backtest, not real trades; n=1 official closed pick |
| 8 | COMMODITY `multi_asset_copytrader` | REJECT | n=186 closed picks | WR 0% unresolved, all force-closed toxic | WR=93.8% claim debunked; all picks force-closed toxic |
| 9 | PENNY_STOCK `skyrocket_detector` | REJECT | n=0 (count=0, picks=[]) | No resolved trades | Not wired to production; MAX_PRICE=20 not $2-5; penny_stock_strategy_harness zero callers |
| 10 | Mutual Funds (active) | NOT REGISTERED | n=0 active picks | Class id = -1; emit_now=False | Daily NAV, no intraday TP/SL possible |

**VERDICT: PROVEN — None.**  
No candidate qualifies as FORWARD-SUPPORTED. Every strategy fails at least one Phase 4 gate.  
**Closest candidate for forward testing:** EQUITY `stocks_rsi2_pullback` (n=78, PF 1.11, WR 44.9%) — but requires n≥100 and must pass SPY benchmark gate (currently failed: t=1.05, median excess -0.57%).

---

## Candidate 1: EQUITY `stocks_rsi2_pullback`

### Hypothesis and implementation

- **Economic rationale:** RSI(2) mean reversion — buy oversold pulls in uptrend (Connors & Alvarez, 2008). Historically worked in 2008-2020 era; post-2020 regime may have decayed.
- **Instruments / universe:** US equity ETFs and stocks (SPY, QQQ, IWM, TMO, PFE, AVGO, etc.)
- **Signal / entry:** RSI(2) < 10 AND close > EMA(200)
- **Exit / TP-SL:** Exit RSI(2) > 70 or max 5 bars; ATR-based stops (variable)
- **Parameter values / ranges:** RSI(2) threshold 10; EMA(200); max hold 5 bars; selection procedure: pre-registered
- **Sizing / exposure:** Kelly × 0.25; position_size_scalar varies per symbol
- **Portfolio accounting:** Single positions; no overlap tracking documented
- **Frictions:** SLIPPAGE_BPS=10 (equity); commission not separately modeled in strategy code
- **Data range / source:** `closed_picks.json` n=34 (phase2), `active_picks.json` n=3 active; source timestamps 2026-11
- **Registration timestamp / hypothesis ID:** Not pre-registered; hypothesis ID not assigned

### Experiment and validity

| Test | Design / period / sample | Statistic and threshold fixed before testing | Result and uncertainty | Pass / fail / inconclusive | Evidence |
|---|---|---|---|---|---|
| Training / selection | phase2 n=34 | WR ≥ 50%, PF ≥ 1.15 | WR 52.94%, PF 1.522 | PASS on stats | `peer_claude-phase10b-money-maker-EQUITY_result_2026-05-31.md` |
| Nested walk-forward folds | None performed | WFE > 0.6 | Not performed | FAIL — not done | N/A |
| Untouched holdout | None performed | n ≥ 60 | Not performed | FAIL — not done | N/A |
| Benchmark / dependence | vs SPY total return | mean excess > 0, t ≥ 2.0 | t=1.05 < 2.0; beat-SPY 45.53%; median excess -0.57% | **FAIL** | `equity_vs_spy.json` |
| Multiple trials / selection | Unknown total trials | Bonferroni/Holm | Unknown trial count | FAIL — trial count unknown | N/A |
| Negative/null controls | Shuffle control | Shuffled prices must not profit | Not performed | FAIL — not done | N/A |
| Costs / params / regime stress | SLIPPAGE_BPS=10 | Cost-adjusted PF ≥ 1.15 | Cost coverage 3.23× (marginal) | PASS on cost | `per_class_cost_gate.json` |
| Frozen prospective paper test | None | n ≥ 100 over 3 months | Zero forward closes | FAIL — no forward test | N/A |

### Metrics

| Metric | Gross | Net | Benchmark / difference | Interval, definition, caveat |
|---|---:|---:|---:|---|
| Annualized return / CAGR | Not computed | Not computed | Not computed | Not computed |
| Sharpe ratio | Not computed | Not computed | Not computed | Not computed |
| Sortino ratio | Not computed | Not computed | Not computed | Not computed |
| Calmar ratio | Not computed | Not computed | Not computed | Not computed |
| Max drawdown | Not computed | Not computed | Not computed | Not computed |
| Win rate | 52.94% | 52.94% | ≥50% target | phase2 n=34 |
| Profit factor | 1.522 | 1.522 | ≥1.15 threshold | phase2 n=34 |
| Expectancy / trade | Not computed | Not computed | Not computed | Not computed |
| Avg holding period | Not computed | Not computed | Not computed | Not computed |
| Longest losing streak | Not computed | Not computed | Not computed | Not computed |
| Skewness / kurtosis | Not computed | Not computed | Not computed | Not computed |
| Serial autocorrelation | Not computed | Not computed | Not computed | Not computed |

**Verdict:** REJECT — n=34 < 100 minimum; SPY beat rate 45.53% < 50%; median excess -0.57% vs SPY; t-stat 1.05 < 2.0.  
**Reason:** Fails SPY benchmark gate (the single most important gate for equity). Despite positive PF on n=34, sample too small and no alpha vs benchmark.

---

## Candidate 2: BOND `bond_connors_rsi2`

### Hypothesis and implementation

- **Economic rationale:** Connors RSI(2) mean reversion on bond ETFs (TLT, IEF, LQD) — buy oversold dips in bond ETFs
- **Instruments / universe:** TLT, IEF, LQD
- **Signal / entry:** RSI(2) < 10, close > SMA200
- **Exit / TP-SL:** Exit RSI(2) > 70 or max 5 bars; TP +2%, SL = max(SMA200, entry×0.98)
- **Parameter values:** RSI(2) threshold 10; EMA(200); TP +2% fixed; max hold 5 bars
- **Sizing:** ATR-based position sizing
- **Portfolio accounting:** Single positions; no overlap tracking
- **Frictions:** SLIPPAGE_BPS=8 (bond); commission not separately modeled
- **Data range:** 2005-01-01 to 2026-05-17 (hypothetical backtest)
- **Registration:** Not pre-registered; hypothesis ID not assigned

### Experiment and validity

| Test | Design / period / sample | Statistic and threshold | Result | Pass / fail | Evidence |
|---|---|---|---|---|---|
| Training / selection | 2005-2026 single backtest | WR ≥ 50%, PF ≥ 1.15 | WR 50.25%, PF 1.3383 | PASS on stats | `bond_connors_rsi2_backtest.json` |
| Nested walk-forward | None | WFE > 0.6 | Not performed | FAIL — not done | N/A |
| Untouched holdout | None | n ≥ 60 | Not performed | FAIL — not done | N/A |
| Benchmark | vs buy-and-hold TLT | Risk-adjusted excess | Not computed | FAIL — not done | N/A |
| Multiple testing | Unknown | Bonferroni/Holm | Unknown | FAIL — unknown | N/A |
| Negative controls | Shuffle control | Shuffled must not profit | Not performed | FAIL — not done | N/A |
| Costs | SLIPPAGE_BPS=8 | Cost-adjusted PF | Not modeled | FAIL — not modeled | N/A |
| Forward test | None | n ≥ 100, 3 months | Zero forward closes | FAIL — not done | N/A |

### Metrics

| Metric | Gross | Net | Benchmark / difference | Interval |
|---|---:|---:|---:|---|
| CAGR | Not computed | Not computed | Not computed | 2005-2026 |
| Sharpe | 2.2163 | Not computed | Not computed | Annualized |
| Max drawdown | 17.79% | Not computed | ≤20% target | Backtest period |
| Win rate | 50.25% | 50.25% | ≥50% | 201 closed of 269 |
| Profit factor | 1.3383 | 1.3383 | ≥1.15 | 201 closed |
| Expectancy / trade | $25.40 | Not computed | Not computed | Per trade |
| Expired trades | 68 (25%) | Excluded from WR/PF | — | Shadow-tracker alignment |

**Verdict:** REJECT — Hypothetical backtest only, not real executed trades. No walk-forward folds. No cost model applied. 68 of 269 trades (25%) expired and excluded from WR/PF calculation.

---

## Candidate 3: CRYPTO `prediction_market_consensus`

### Hypothesis and implementation

- **Economic rationale:** Prediction market consensus (Kalshi/Polymarket) as alpha signal for crypto direction
- **Instruments / universe:** Crypto symbols (BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT, ADA-USD, etc.)
- **Signal / entry:** Prediction market consensus signals (Kalshi + Polymarket reverse)
- **Exit / TP-SL:** Varies by symbol (BNBUSDT TP ~13%, SL ~8%; BTCUSDT TP ~13%, SL ~8%)
- **Parameters:** consensus_count=2; confidence threshold 0.70-0.91
- **Sizing:** Unknown — not documented in pick files
- **Portfolio accounting:** Single positions; no overlap tracking
- **Frictions:** Not modeled
- **Data range:** 2026-11-15 (2 OPEN picks, 0 resolved)
- **Registration:** Not pre-registered

### Experiment and validity

| Test | Design / period / sample | Statistic and threshold | Result | Pass / fail | Evidence |
|---|---|---|---|---|---|
| Training / selection | Backtest n=89 | WR ≥ 50%, PF ≥ 1.15 | WR 89.89%, PF 24.51 | PASS on stats | `kimi_ultimate_proven_edge_2026-05-16.md` |
| Nested walk-forward | None | WFE > 0.6 | Not performed | FAIL — not done | N/A |
| Untouched holdout | None | n ≥ 100 | Zero forward closes | FAIL — not done | N/A |
| Benchmark | vs buy-and-hold crypto | Risk-adjusted excess | Not computed | FAIL — not done | N/A |
| Multiple testing | Unknown total trials | PBO ≤ 0.10 | PBO 0.603 | **FAIL** — 60.3% overfitting probability | `kimi_ultimate_proven_edge_2026-05-16.md` |
| Negative controls | Shuffle control | Shuffled must not profit | Not performed | FAIL — not done | N/A |
| Costs | Not modeled | Breakeven cost level | Not computed | FAIL — not modeled | N/A |
| Forward test | n=110 shadow mode | n ≥ 100 over 3 months | n=110 shadow, 0 live | FAIL — shadow only | `prediction_market_consensus_dashboard.json` |

### Metrics

| Metric | Gross | Net | Benchmark / difference | Interval |
|---|---:|---:|---:|---|
| Win rate | 89.89% | 89.89% | ≥50% | Backtest n=89 |
| Profit factor | 24.51 | 24.51 | ≥1.15 | Backtest n=89 |
| DSR | 9.36 | Not computed | ≥0.95 | Backtest |
| PBO | 0.603 | Not computed | ≤0.10 | **FAIL** |
| Forward WR | 79.09% | 79.09% | ≥50% | Shadow n=110 |
| Forward PF | 13.20 | 13.20 | ≥1.15 | Shadow n=110 |
| Forward picks live | 0 | 0 | n ≥ 100 live | pick_count=0 |

**Verdict:** REJECT — PBO 0.603 >> 0.10 gate (60.3% probability the backtest edge is overfitting). Zero resolved forward trades. `pick_count: 0` in `prediction_market_picks.json`. Claimed 85-100% WR contradicted by actual closed_picks.json data (56.60% WR, PF 0.6054 on 76 CRYPCO picks).

---

## Candidate 4: ETF `etf_rsi2_pullback` / `etf_dual_momentum` / `etf_faber_tactical`

### Hypothesis and implementation

- **Economic rationale:** ETF tactical allocation — buy when close > SMA200 (Faber 2007), RSI(2) mean reversion, dual momentum
- **Instruments / universe:** SPY, QQQ, EFA, IEF, GLD, sector ETFs (XLK, XLF, XLE, XLV, etc.)
- **Signal / entry:** Close > SMA200; RSI(2) < 10; top 3 by 12m return
- **Exit / TP-SL:** Close < SMA200 (Faber); RSI(2) > 70; ATR-based TP/SL (tp_mult=2.5, sl_mult=1.5)
- **Parameters:** SMA200; RSI(2) threshold 10; ATR(14); min RR 1.20
- **Sizing:** Not documented
- **Portfolio accounting:** Single positions
- **Frictions:** SLIPPAGE_BPS=10 (equity); not modeled in strategies
- **Data range:** 2020-2026 (claimed); actual closed_picks: 1 pick
- **Registration:** Not pre-registered

### Experiment and validity

| Test | Design / period / sample | Statistic and threshold | Result | Pass / fail | Evidence |
|---|---|---|---|---|---|
| Training / selection | Claimed n=107 | WR ≥ 50%, PF ≥ 1.15 | n=1 closed pick, WR 0%, PF 0.00 | **FAIL** — n=1 | `closed_picks.json` |
| Nested walk-forward | Claimed WFE 100% | WFE > 0.6 | Not performed on real data | FAIL — not on real data | `money-maker-action-plan.md` claim |
| Untouched holdout | None | n ≥ 60 | n=1 | FAIL — n=1 | `closed_picks.json` |
| Benchmark | vs buy-and-hold ETF | Risk-adjusted excess | Not computed | FAIL — not done | N/A |
| Multiple testing | Unknown | Bonferroni/Holm | Unknown | FAIL — unknown | N/A |
| Negative controls | Shuffle control | Shuffled must not profit | Not performed | FAIL — not done | N/A |
| Costs | SLIPPAGE_BPS=10 | Cost-adjusted PF | Not modeled | FAIL — not modeled | N/A |
| Forward test | 14 OPEN picks | n ≥ 100 over 3 months | 0 resolved | FAIL — 0 resolved | `active_picks_etf.json` |

### Metrics

| Metric | Gross | Net | Benchmark / difference | Interval |
|---|---:|---:|---:|---|
| Win rate | 0.0% | 0.0% | ≥50% | n=1 closed pick |
| Profit factor | 0.00 | 0.00 | ≥1.15 | n=1 closed pick |
| Max drawdown | Not computed | Not computed | ≤20% | n=1 |
| Expectancy / trade | -0.01% | -0.01% | Not computed | QQQ lost 0.01% |

**Verdict:** REJECT — n=1 closed pick. Claimed 56.1% WR / 1.34 PF does not match ground truth. 134 TIME_EXIT picks with forced pnl_pct=0 (resolver bug). 14 OPEN picks with zero realized PnL.

---

## Candidate 5: FOREX `multi_asset_copytrader`

### Hypothesis and implementation

- **Economic rationale:** Copy trader consensus on FOREX pairs
- **Instruments / universe:** FOREX pairs (EURJPY=X, USDJPY=X, GBPJPY=X, AUDJPY=X, CADJPY=X)
- **Signal / entry:** Copy trader consensus direction
- **Exit / TP-SL:** Unknown — not documented
- **Parameters:** Not documented
- **Sizing:** Not documented
- **Portfolio accounting:** Single positions
- **Frictions:** SLIPPAGE_BPS=8 (forex); not modeled
- **Data range:** 2026-11 (n=176 closed picks)
- **Registration:** Not pre-registered

### Experiment and validity

| Test | Design / period / sample | Statistic and threshold | Result | Pass / fail | Evidence |
|---|---|---|---|---|---|
| Training / selection | n=176 closed picks | WR ≥ 50%, PF ≥ 1.15 | WR 13.64% (of all n), PF 0.6596 | **FAIL** | `closed_picks.json` |
| Nested walk-forward | None | WFE > 0.6 | OOS PF 0.4829 | FAIL — OOS PF < 1.0 | `money_ready_verdict.json` |
| Untouched holdout | None | n ≥ 60 | n=176 ≥ 60 | PASS on n | `closed_picks.json` |
| Benchmark | vs buy-and-hold FOREX | Risk-adjusted excess | Not computed | FAIL — not done | N/A |
| Multiple testing | Unknown | Bonferroni/Holm | Unknown | FAIL — unknown | N/A |
| Negative controls | Shuffle control | Shuffled must not profit | Not performed | FAIL — not done | N/A |
| Costs | SLIPPAGE_BPS=8 | Cost-adjusted PF | Not modeled | FAIL — not modeled | N/A |
| Forward test | None | n ≥ 100 over 3 months | Zero forward closes | FAIL — not done | N/A |

### Metrics

| Metric | Gross | Net | Benchmark / difference | Interval |
|---|---:|---:|---:|---|
| Win rate | 13.64% | 13.64% | ≥50% | n=176 |
| Profit factor | 0.6596 | 0.6596 | ≥1.15 | Policy-clean net |
| Max drawdown | 82% | 82% | ≤20% | `money_ready_verdict.json` |
| Expectancy / trade | Not computed | Not computed | Not computed | Not computed |

**Verdict:** REJECT — PF 0.6596 < 1.15; MDD 82% > 20%; walk-forward OOS PF 0.4829 < 1.0; policy_frozen=true; bootstrap CI crosses zero (lower bound -0.000194).

---

## Candidates 6-10: FUTURES, BOND, COMMODITY, PENNY_STOCK, Mutual Funds (active)

| Candidate | Verdict | Primary blocker |
|---|---|---|
| FUTURES `multi_asset_copytrader` | REJECT | All 31 picks force-closed toxic (pnl=$0); stale 246 days |
| BOND `bond_duration_rotation` | REJECT | Hypothetical backtest only; n=1 official closed pick |
| COMMODITY `multi_asset_copytrader` | REJECT | All 186 picks force-closed toxic; WR=93.8% claim debunked |
| PENNY_STOCK `skyrocket_detector` | REJECT | n=0 resolved; not wired to production; MAX_PRICE=20 not $2-5 |
| Mutual Funds (active) | NOT REGISTERED | Class id = -1; daily NAV, no intraday TP/SL |

---

## Pre-Registered Forward Test Protocol

See `PROOF_PROTOCOL.md` (separate document) for the full pre-registered forward-test protocol including duration, rules, live tracking URL, and decision thresholds.

---

## Rejected Strategies (Do Not Re-test)

| Strategy | Reason | File |
|---|---|---|
| CRYPTO `kimi_inverse_scanner` | TP 2% / SL 3% (R:R 0.67); 28 picks generated, 0 resolved | `alpha_engine/kimi_inverse_scanner.py` |
| CRYPTO `kimi_vpin_lgbm_ensemble` | No resolved trades found | `baby_strategies/kimi_vpin_lgbm_ensemble.py` |
| CRYPTO `kimi_ema600_40_momentum` | No resolved trades found | `baby_strategies/kimi_ema600_40_momentum.py` |
| PENNY_STOCK `skyrocket_detector` | Not wired to production; count=0 | `alpha_engine/strategies/skyrocket_detector.py` |
| PENNY_STOCK `penny_stock_strategy_harness` | Zero callers outside itself | `alpha_engine/penny_stock_strategy_harness.py` |

---
