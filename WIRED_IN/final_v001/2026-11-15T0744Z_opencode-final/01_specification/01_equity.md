# 01_SPECIFICATION — EQUITY (US Stocks / ETFs)

**Asset Class:** EQUITY (US equities and equity ETFs)
**Status:** RESEARCH SLOT ONLY — NOT MONEY-READY
**sizing_allowed:** false
**Source:** `alpha_engine/data/closed_picks.json`, `alpha_engine/data/active_picks.json`, `final_v3/quant-audit-2026-11-14/04_asset_class_fixes/ASSET_CLASS_FIXES.md`, `reports/peer_claude-phase10b-money-maker-EQUITY_result_2026-05-31.md`

---

## 1. Algorithm Specification

### Strategies Attempted

| Strategy | File | Parameters | Entry Logic | Exit Logic | TP/SL | Result |
|----------|------|-----------|-------------|------------|-------|--------|
| `cta_golden_cross_200` | `alpha_engine/data/closed_picks.json` | SMA50/SMA200, ADX>30 | LONG only, SMA50>SMA200 | SMA50<SMA200 | 3.0% TP / 3.0% SL (R:R 1.0) | 6 closed picks, 5 WON/1 LOST, WR 83.3%, PF 7.45, MDD ~3.28% |
| `stocks_rsi2_pullback` | `baby_strategies/` | RSI(2)<10, close>EMA(200) | LONG on RSI(2)<10 | RSI(2)>70 or max 5 bars | ATR-based | n=78 closed, WR 44.9%, PF 1.11 (phase10b); n=34, WR 52.94%, PF 1.522 (phase2) |
| `regime_mild_bull` | `alpha_engine/` | Regime-based | LONG in mild bull regime | Regime change | Unknown | n=6, WR 66.7%, PF 1.39 (tiny n) |
| `regime_accumulation` | `alpha_engine/` | Regime-based | LONG in accumulation regime | Regime change | Unknown | n=14, WR 57.1%, PF 0.70 |
| `regime_mild_bear` | `alpha_engine/` | Regime-based | SHORT in mild bear regime | Regime change | Unknown | n=25, WR 24.0%, PF 0.09 |
| `regime_strong_bear` | `alpha_engine/` | Regime-based | SHORT in strong bear regime | Regime change | Unknown | n=11, WR 0.0%, PF 0.00 |

### Cost Model
- Commission: 0.10% per side (equity ETF typical)
- Slippage: included in slippage_bps=10 (money_ready_verdict.py)
- Round-trip cost: 0.20% (20 bps)
- Source: `alpha_engine/money_ready_verdict.py`, `SLIPPAGE_BPS["EQUITY"] = 10.0`

### Benchmark
- SPY total return (dividends adjusted)
- Must beat on risk-adjusted basis, not just raw return
- Source: `final_v3/05_evidence/equity_vs_spy.json`

### Walk-Forward Design
- Not yet implemented for equity strategies
- Required: 5 folds, expanding window, 1yr train / 1yr test
- Source: `final_v3/quant-audit-2026-11-14/03_backtest_simulation/BACKTEST_FIXES.md`

---

## 2. Backtest Results (Ground Truth from closed_picks.json)

**File:** `alpha_engine/data/closed_picks.json` (filter: `category == "equity"` OR `asset_class == "EQUITY"`)

| Metric | Value |
|--------|-------|
| Total closed equity picks | 10 |
| Wins (WON) | 9 |
| Losses (LOST) | 1 |
| Win Rate | 90.00% |
| Profit Factor | 7.45 |
| Gross Profit | +24.44% |
| Gross Loss | -3.28% |
| Net PnL | +21.16% |
| Max Drawdown | ~3.28% (single QQQ loss) |

### Individual Trades (All LONG, all `cta_golden_cross_200`)

| Symbol | Direction | Entry | Exit | PnL | Status |
|--------|-----------|-------|------|-----|--------|
| QQQ | LONG | ? | ? | -3.28% | LOST |
| SPY | LONG | ? | ? | +3.64% | WON |
| SPY | LONG | ? | ? | +3.64% | WON |
| SPY | LONG | ? | ? | +3.69% | WON |
| SPY | LONG | ? | ? | +3.69% | WON |
| SPY | LONG | ? | ? | +3.73% | WON |

### Critical Observation
All 6 verified `asset_class: EQUITY` entries are the SAME strategy (`cta_golden_cross_200`) on SPY/QQQ only, all LONG. This is not a diversified equity edge — it's one SMA crossover trade repeated 6 times on two symbols.

### Phase 2 Performance Audit
**File:** `reports/peer_claude-phase2-perf-equity_result_2026-05-31.md`

| Metric | Value |
|--------|-------|
| Total trades (raw, all closed with non-null PnL) | 131 |
| TP_HIT WR | 27.5% (36/131) |
| PnL>0 WR | 31.3% (41/131) |
| Profit Factor | 0.708 |
| Avg PnL per trade | -0.449% |
| Total PnL | -38.16% |
| Max Drawdown proxy | 79.0% |

**Verdict: FAIL on every T2 axis (PF≥1.5, WR≥50%, MDD<20, n≥100).** No equity strategy passes Tier-2 money-ready gates.

---

## 3. Equity vs SPY Benchmark Gate — FAILED

**File:** `final_v3/05_evidence/equity_vs_spy.json` (93 lines)

| Gate | Requirement | Result | Status |
|------|-------------|--------|--------|
| G1 | n ≥ 100 | 738 | PASS |
| G2 | mean excess > 0 | +0.2092% | PASS |
| G3 | t ≥ 2.0 | 1.0541 | **FAIL** |
| G4 | mean excess > cost (0.10%) | +0.21 > 0.10 | PASS |
| **VERDICT** | — | **NO_ALPHA_BETA** | **FAILED** |

**Full detail:**
- n_usable: 738
- mean_pnl_pct: +0.3230%
- mean_bench_pct (SPY): +0.1138%
- mean_excess_pct: +0.2092%
- median_excess_pct: **-0.5726%**
- t_statistic: 1.0541
- beat-SPY rate: 45.53%
- cost_pct_used: 0.1%

**Interpretation:** The mean excess return is positive (+0.21%) but driven by a right tail — the median pick underperforms SPY by -0.57%. 54.53% of equity picks lose to simple buy-and-hold SPY. This is beta capture, not alpha.

---

## 3. Per-Class Cost Coverage

**File:** `config/per_class_cost_gate.json`

| Metric | Value |
|--------|-------|
| Class | EQUITY |
| n | 738 |
| mean_pnl_pct | 0.323 |
| cost_pct | 0.1 |
| cost_multiple | 3.23 |
| after_cost_net_per_trade | 0.223 |
| required_mean_pnl_pct | 0.3 |
| allowed | true |
| sample_sufficient | true |

Rule: `class mean pnl_pct >= 3.0x round-trip cost` (min sample 30)

**EQUITY passes the 3x cost gate** — but this only means costs are covered, not that there's alpha. The SPY gate proves there's no edge beyond beta.

---

## 4. Per-Class Cost Gate Report

**File:** `alpha_engine/data/per_class_cost_gate_report.txt`

| Class | n | Cost Multiple | Verdict |
|-------|-----|---------------|---------|
| BOND | 35 | -4.41× | BLOCK |
| COMMODITY | 7 | -3.98× | BLOCK (insufficient sample) |
| CRYPCO | 1,966 | -1.42× | BLOCK |
| EQUITY | 738 | 3.23× | **ALLOW** |
| ETF | 567 | 0.40× | BLOCK |
| FOREX | 187 | -1.94× | BLOCK |

EQUITY is the ONLY class that passes the 3x cost gate. But passing the cost gate only means gross profits exceed costs — it does NOT mean there's alpha over beta.

---

## 5. Key Metrics

| Metric | Value | Threshold | Pass/Fail |
|--------|-------|-----------|-----------|
| Total Trades | 10 | ≥ 50 | FAIL |
| Win Rate | 90.00% | ≥ 50% | PASS (but n too small) |
| Profit Factor | 7.45 | ≥ 1.5 | PASS (but n too small) |
| Net PnL | +21.16% | > 0 | PASS (but n too small) |
| Max Drawdown | ~3.28% | ≤ 20% | PASS |
| Sharpe Ratio | Not computed | ≥ 1.0 | UNKNOWN |
| DSR | Not computed | ≥ 0.95 | UNKNOWN |
| PBO | Not computed | ≤ 0.10 | UNKNOWN |
| SPY Beat Rate | 45.53% | > 50% | FAIL |
| Median Excess vs SPY | -0.57% | > 0% | FAIL |
| t-Statistic | 1.0541 | ≥ 2.0 | FAIL |
| Cost Coverage | 3.23× | ≥ 3.0× | PASS |

---

## 6. Pick Justification

**No equity pick is justified for deployment.**

**Reasoning:**
1. **n=10 is statistically insufficient** — cannot draw conclusions from 10 trades
2. **All 6 verified picks are the same strategy** (`cta_golden_cross_200`) on only 2 symbols (SPY, QQQ), all LONG
3. **SPY gate FAILED** — t=1.05 < 2.0, median excess -0.57%, beat-SPY rate 45.53%
4. **Phase 2 audit: PF 0.708 < 1.5, WR 31.3% < 50%** on 131 closed trades
5. **DSR and PBO not computed** — cannot rule out overfitting
6. **100% LONG bias** — no short-side edge exists

**Best (least bad) equity candidate:** None. All equity strategies fail.

---

## 7. Elimination Reason

- **RSI(2) Mean Reversion (Equity):** Eliminated — PF 0.708 < 1.5, WR 31.3% < 50% on n=34; full backtest on 7 equity ETFs over 2020-2025 showed net PnL -118% to -186%
- **Dual MA Crossover (Equity):** Eliminated — WR 0-17%, PF ~0 on post-2020 data
- **Bollinger Mean Reversion (Equity):** Eliminated — negative expectancy (-17% to -33%), Sharpe -1.2 to -2.0
- **CTA Golden Cross (Equity):** Eliminated — 6 trades on SPY/QQQ only, all LONG, SPY gate failed (t=1.05, median excess -0.57%)
- **All Equity Strategies:** Eliminated — 0/7 money-ready gates passed; no alpha beyond SPY beta

---

## 8. Money-Ready Gate Result

**0/7 gates passed.** Best was EQUITY cost coverage (3.23×) but this only means costs are covered, not that there's alpha. The SPY gate proves there is no excess return beyond beta.

**EQUITY remains a research slot only — not deployable.**
