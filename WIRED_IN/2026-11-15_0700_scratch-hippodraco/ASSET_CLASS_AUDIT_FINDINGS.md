# ASSET CLASS AUDIT — Consolidated Findings
**Repo:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/
**Audit date:** 2026-11-15
**Status:** All seven asset classes audited against ground-truth data. **Zero asset classes are proven profitable.**

---

## Executive Summary

After forensically auditing every asset class against actual repo data (`closed_picks.json` with 503 picks, `active_picks.json` with 89 picks, `quality_gates.py`, `money_ready_verdict.json`, `pf_registry.json`, strategy source code, and all audit reports), **no asset class passes all money-ready proof gates**. Every class is either blocked, insufficient data, or research-only.

**Bottom line: Do not deploy capital to any asset class as an active prediction strategy.** The only justified capital deployment is low-cost ETF/MF passive allocation (beta capture), not alpha hunting.

---

## Per-Asset-Class Ground Truth

### 1. EQUITY — RESEARCH SLOT ONLY, NOT DEPLOYABLE

| Metric | Value |
|--------|-------|
| Closed picks (n) | 10 |
| Wins / Losses | 9 / 1 |
| Win Rate | 90.00% |
| Profit Factor | 7.45 |
| **SPY benchmark gate (t ≥ 2.0)** | **1.05 — FAILED** |
| Beat-SPY rate | 45.53% |
| Median excess vs SPY | **-0.57%** |
| Direction bias | **100% LONG** |

**Evidence:** `alpha_engine/data/closed_picks.json` — all 6 verified entries are `cta_golden_cross_200` on SPY/QQQ, all LONG. `final_v3/05_evidence/equity_vs_spy.json` — SPY gate FAILED (t=1.05 < 2.0). `final_v3/quant-audit-2026-11-14/04_asset_class_fixes/ASSET_CLASS_FIXES.md` — EQUITY official PF=0.939 (<1.0), registry PF=0.662.

**Verdict:** RESEARCH SLOT ONLY. EQUITY clears its cost gate (3.23×) but cannot beat SPY. The median equity pick loses to buy-and-hold the index. All active picks are LONG-biased — no short-side edge.

---

### 2. CRYPTO — BLOCKED (Negative Expectancy)

| Metric | Value |
|--------|-------|
| Closed picks (n) | 76 |
| Wins / Losses | 30 / 23 |
| Win Rate | 56.60% |
| **Profit Factor** | **0.6054** |
| **Expectancy** | **-0.89% total** |
| **CRYPCO expectancy** | **-5.86%, CI [-4.96%, -4.38%]** |
| **PBO** | **0.603** (≥0.10 gate = FAIL) |
| Forward closes | **Zero resolved** |

**Evidence:** `alpha_engine/data/closed_picks.json` — 76 CRYPCO picks, 56.60% WR but PF 0.6054 (losses 1.65× larger than wins). `final_v3/quant-audit-2026-11-14/01_audit/AUDIT_FINDINGS.md` — CRYPCO expectancy -5.86%, statistically significant NEGATIVE. `backtest_results/kimi_cursor_v04_comparison.json` — all KIMI strategies PF ≤1.357, mostly negative returns. `reports/kimi_ultimate_proven_edge_2026-05-16.md` — claimed 85-100% WR for ML tokens **contradicted** by actual data (56.60% actual WR, PF 0.6054).

**Verdict:** BLOCKED. Negative expectancy after costs. PBO=0.603 means 60.3% probability the apparent edge is overfitting. No clean forward test exists (all picks stuck OPEN).

---

### 3. ETF — BLOCKED (Cohort Mismatch + Empty Data)

| Metric | Value |
|--------|-------|
| Closed picks (n) | **1** |
| Wins / Losses | 0 / 1 |
| Win Rate | **0.0%** |
| Profit Factor | **0.00** |
| Claimed (action plan) | n=107, WR 56.1%, PF 1.34 — **does not match ground truth** |

**Evidence:** `alpha_engine/data/closed_picks.json` — exactly 1 ETF closed pick (QQQ via `etf_faber_tactical`, LOST at -0.01%). `alpha_engine/data/active_picks_etf.json` — 14 OPEN picks, none resolved. `alpha_engine/data/etf_decay_picks.json` and `etf_sector_picks.json` — OPEN picks only, `forward_test_only: true`, zero realized PnL.

**Verdict:** BLOCKED. Claimed 56.1% WR/1.34 PF does not match ground truth (0% WR, PF=0.00 on n=1). 134 ETF picks stuck at TIME_EXIT with forced `pnl_pct=0` (resolver bug). No ETF strategy passes any Phase 4 gate.

---

### 4. MUTUAL FUNDS — NOT REGISTERED AS ASSET CLASS

| Metric | Value |
|--------|-------|
| Class ID in `asset_class.py` | **Does not exist** |
| Gatekeeper `ASSET_CLASS_MAP` ID | **-1 (NOT_BUILT)** |
| Mutual fund active picks emitted | **Zero** |
| Mutual fund walk-forward results | **n = 0 (file does not exist)** |
| Mutual fund metadata | 8 funds (sample JSON), not 38 |

**Evidence:** `alpha_engine/asset_class.py` — classes: crypto/forex/futures/bond/etf/equity/unknown. No MUTUAL_FUND. `ml_gatekeeper/gatekeeper.py:73` — ASSET_CLASS_MAP has 7 classes (CRYPTO=0…FUTURES=6), MUTUAL_FUND resolves to -1. `alpha_engine/pick_failure_root_cause.py:64-70` — `emit_now: False`, "Never promote as an active pick", `horizon_hours: None`.

**Structural incompatibility:** Mutual funds strike NAV once daily after close. No intraday TP/SL possible. No intraday price mark. Load/12b-1 costs. Frequent-trading limits. T+1 settlement.

**Verdict:** VALID as **passive core allocation** only (60% US equity, 20% international, 20% bonds/T-bills, ER ≤0.09%, turnover ≤20%, track record ≥10y, no load, no 12b-1). 2 of 8 sample funds pass hard gates (FXAIX at 0.015% ER/$0 min, SWTSX at 0.03% ER/$0 min). NOT valid as active prediction picks.

---

### 5. BOND — BLOCKED (Insufficient Data)

| Metric | Value |
|--------|-------|
| Closed picks (n) | **1** |
| Wins / Losses | 0 / 1 |
| Win Rate | **0.0%** |
| Profit Factor | **0.000** |
| Minimum n for statistical inference | **100** |

**Evidence:** `alpha_engine/data/active_picks_bond.json` — 6 active picks, all OPEN (unresolved). `audit_dashboard/data/pf_registry.json` — BOND: n=1, PF=0.000, WR=0.00% across all views. `alpha_engine/money_ready_verdict.py` — `MIN_N_CLASS = 100`. `final_v3/quant-audit-2026-11-14/04_asset_class_fixes/ASSET_CLASS_FIXES.md` — BOND: n=1, INSUFFICIENT_DATA.

**Hypothetical backtests exist** (Connors RSI2 n=201 closed, credit spread overlay n=173-224, duration rotation n=279) but these are simulations, not real trades.

**Verdict:** BLOCKED. n=1 cannot support statistical inference. Need yield/duration data pipeline and n≥100 before any evaluation.

---

### 6. FOREX — BLOCKED (Negative Expectancy)

| Metric | Value |
|--------|-------|
| Closed picks (n) | 176 |
| Wins / Losses | 24 / 26 |
| Win Rate | 13.64% (of all n), 48.0% (of resolved) |
| Profit Factor | 0.6596 (policy-clean), 0.8385 (recent) |
| Max Drawdown | **82%** |
| Historical (May 2026) | PF ~0.27, −1026% PnL |

**Evidence:** `alpha_engine/data/closed_picks.json` — 176 FOREX picks, 97 (55%) stuck FLAT/unresolved. `audit_dashboard/data/money_ready_verdict.json` — FOREX: policy_frozen=true, MDD=82% (mdd_ok=false), bootstrap CI crosses zero, walk-forward OOS PF=0.4829 (wf_oos_ok=false). `reports/peer_claude-phase10b-money-maker-FOREX_result_2026-05-31.md` — expectancy -4.58%/pick, every gate failed.

**Verdict:** BLOCKED. PF 0.66-0.84 vs 1.5 floor. MDD 82%. Policy frozen. No credible path.

---

### 7. FUTURES — BLOCKED (Stale + All Force-Closed Toxic)

| Metric | Value |
|--------|-------|
| Closed picks (n) | **31** |
| Wins / Losses | **0 / 0** |
| All statuses | CLOSED (force-closed toxic) |
| All PnL | **$0.00** |
| Last pick date | **246 days ago** (2026-03-13) |
| DSR | **0.0075** (fail) |

**Evidence:** `alpha_engine/data/closed_picks.json` — 31 FUTURES picks, all CLOSED, all pnl_pct=0, all exit_reason=FORCE_CLOSED_TOXIC. `audit_dashboard/data/money_ready_verdict.json` — FUTURES: policy_frozen=true, n_ok=false (n=13 < 100), recency_ok=false, DSR OK=false. `alpha_engine/strategy_blocklist.py:229` — `futures_momentum` blocked. `alpha_engine/smart_picks_engine.py:290-291` — blocked (0% WR on 56 closed, PF 0.00).

**Verdict:** BLOCKED. Stale (246 days since last pick), insufficient n, all picks zero-PnL force-closes. `multi_asset_copytrader` FUTURES blocked in `quality_gates.py:2715`.

---

### 8. Penny Stocks / $2-5 Stocks — KEEP BLOCKED

| Source | Asset | n | WR | PF | Status |
|--------|-------|---|-----|-----|--------|
| ASSET_CLASS_FIXES.md | MEME | 10 | 10.00% | 0.023 | Keep blocked |
| ASSET_CLASS_FIXES.md | PENNY_STOCK | 1 | 0.00% | 0.000 | Keep blocked |
| closed_picks.json | MEME / PENNY_STOCK | 0 | — | — | Not present |
| peer_claude penny result | PENNY | 8 | 28.6% | 0.169 | FAIL all axes |
| groksstuff.txt | penny | 2 | 0.0% | None | p=1.000 |
| swarm_phase2 | PENNY | 45 | 42.2% | 0.85 | Sub-50% |

**Structural reasons against penny stocks:**
- Extreme bid-ask spreads (5-20%+) instantly destroy any edge
- Pump-and-dump risk (watchlist contains SIDU, MULN, BBIG, HYMC, RDBX, etc.)
- Illiquidity — entering/exiting moves price against you
- No fundamental edge (no earnings/revenue or distressed financials)
- Survivorship bias (delisted/bankrupt/reverse-split names excluded from backtests)
- Expected value negative after costs

**`alpha_engine/strategies/skyrocket_detector.py` exists but is NOT wired to production.** `MAX_PRICE=20.0` (not $2-5), dynamic universe `price ≤ 25.0`. `skyrocket_picks.json`: count=0, picks=[]. `penny_stock_strategy_harness.py` (1869 lines) has zero callers outside itself.

**Verdict:** KEEP BLOCKED. Buying 10 penny stocks hoping 1 skyrockets is gambling, not quantitative trading. Expected value is negative after costs.

---

## Unified Conclusion

| Rank | Asset Class | Verdict | Best Evidence | Reason Blocked |
|------|-------------|---------|---------------|----------------|
| 1 | Mutual Funds + ETFs | **Core allocation only** | FXAIX 0.015% ER, SWTSX 0.03% ER | Beta capture, not alpha |
| 2 | EQUITY | Research slot only | Failed SPY gate (t=1.05) | Median excess -0.57% vs SPY |
| 3 | CRYPTO | Blocked | CRYPCO expectancy -5.86%, CI excludes zero | Negative expectancy, PBO=0.603 |
| 4 | ETF | Blocked | n=1 closed pick, WR=0%, PF=0.00 | Cohort mismatch, resolver bug |
| 5 | FOREX | Blocked | PF 0.6596, MDD 82% | Sub-floor expectancy |
| 6 | FUTURES | Blocked | n=31, all $0 PnL, stale 246d | All force-closed toxic |
| 7 | BOND | Blocked | n=1 | Insufficient data |
| 8 | COMMODITY copy-trader | Blocked | n=186, all force-closed toxic | WR=93.8% claim debunked |
| 9 | Mutual Funds (active) | Not registered | Class id = -1 | Daily NAV, no intraday TP/SL |
| 10 | Penny stocks | Blocked | WR 0-42%, PF 0.000-0.85 | Lottery ticket, negative EV |

**No asset class is proven profitable.** Deploy real money only into low-cost index ETF/MF passive allocation.

---

## Recommended Statistical Proof Standard (10 Gates)

No strategy may be called "profitable" unless it passes ALL:

1. **Chronological train/test split** — features computed only from past data, rolling recalibration
2. **Walk-forward optimization** with embedded OOS windows; report walk-forward efficiency
3. **Multiple-testing correction** — state total configurations tried, report deflated Sharpe ratio and/or White's Reality Check p-value
4. **Block-bootstrap Monte Carlo** of trade sequences — report % paths positive after costs, 5th-percentile worst case
5. **Full friction model** — spread, commission, slippage, funding, tax; state breakeven cost level and margin of safety
6. **Statistical significance** — bootstrap CI for mean excess return excluding zero; t-stat and p-values
7. **Regime robustness** — bull/bear/sideways × high/low vol; positive expectancy in majority of regimes
8. **Control experiment** — permuted/shuffled prices must NOT produce similar performance
9. **Pre-registered forward test** — duration, rules, live tracking URL, decision thresholds before real capital
10. **Reproducibility** — fixed seeds, versioned data, exact formulas, runnable code

## Required Statistical & Risk Metrics (compute for every candidate)

- **Returns:** CAGR, cumulative return, annualized volatility
- **Risk-adjusted:** Sharpe, Sortino, Calmar, Sterling, Treynor, Information ratio
- **Drawdown:** max drawdown, average drawdown, recovery time
- **Trade stats:** win rate, profit factor, expectancy per trade, avg win/avg loss, payoff ratio, longest losing streak, avg holding period
- **Distribution:** skewness, kurtosis, serial autocorrelation, fat-tail diagnostics
- **Cost-adjusted net vs gross equity curves**
- **Benchmark comparison** vs buy-and-hold and risk-free
- **Parameter sensitivity** across full sweep

## TP/SL Parameters (from actual repo strategies, for reference only)

| Strategy | TP | SL | R:R | Source |
|----------|-----|-----|-----|--------|
| `etf_rsi2_pullback` | +4% | -2% | 2.0 | `alpha_engine/etf_strategies.py` |
| `kimi_inverse_scanner` | +2.0% | -3.0% | 0.67 | `alpha_engine/kimi_inverse_scanner.py` |
| `kimi_vpin_lgbm_ensemble` | 2-5× ATR | 2-3× ATR | varies | `baby_strategies/kimi_vpin_lgbm_ensemble.py` |
| `kimi_vpin_reversion` | +6% | -3% | 2.0 | `baby_strategies/kimi_vpin_reversion.py` |
| `bond_connors_rsi2` | +2% fixed | max(SMA200, entry×0.98) | varies | `alpha_engine/bond_strategies.py` |
| Genome top-3 configs | 2.0-3.0× ATR | 1.0-1.5× ATR | 1.3-2.0 | `genome/kimi_top_picks_automation.py` |

**None of these strategies have demonstrated positive expectancy after costs on resolved trades.**

---

## File Paths for Every Claim

| Claim | File Path |
|-------|-----------|
| All subagent findings | `WIRED_IN/2026-11-15_0700_scratch-hippodraco/Summary.MD` |
| ETF ground truth | `alpha_engine/data/closed_picks.json`, `alpha_engine/data/active_picks_etf.json` |
| Mutual funds not registered | `alpha_engine/asset_class.py`, `ml_gatekeeper/gatekeeper.py:73` |
| Bond n=1 insufficient | `alpha_engine/money_ready_verdict.py`, `audit_dashboard/data/pf_registry.json` |
| FOREX blocked | `alpha_engine/data/closed_picks.json`, `audit_dashboard/data/money_ready_verdict.json` |
| FUTURES all $0 PnL | `alpha_engine/data/closed_picks.json`, `quality_gates.py:2715` |
| Penny stocks blocked | `final_v3/quant-audit-2026-11-14/04_asset_class_fixes/ASSET_CLASS_FIXES.md` |
| Equity vs SPY gate failed | `final_v3/05_evidence/equity_vs_spy.json` |
| CRYPCO expectancy -5.86% | `final_v3/quant-audit-2026-11-14/01_audit/AUDIT_FINDINGS.md` |
| 0/166 cells fail all gates | `final_v3/quant-audit-2026-11-14/00_summary/COMMON_THEMES.md` |