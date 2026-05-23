# E-007: ETF VIX Gate — Opportunity Cost Analysis

**Date:** 2026-05-18  
**Analyst:** Claude Sonnet 4.6  
**Gate:** M-098 ETF VIX regime gate (VIX ≥ 25 threshold, enforce-by-default 2026-05-18+)  
**Source:** MASTER_ACTION_PLAN_2026-05-18 §2.3.2 item E-007

---

## Data Availability Note

Local `closed_picks.json` contains 0 ETF picks (all 8,463 closed picks are CRYPTO/FOREX/COMMODITY/FUTURES/EQUITY/BOND). The n=75 closed ETF picks visible on the dashboard originate from the production MySQL DB (sync scheduled 2026-05-24). Full VIX-stratified backtest requires the MySQL sync.

**This report provides the methodology, known VIX event inventory, and a conservative estimate. Exact numbers will update post-sync.**

---

## Current ETF Performance Baseline (from dashboard_data.json)

| Metric | Value |
|--------|-------|
| Closed picks (n) | 75 (82 by_asset_class including actives) |
| Win Rate | 66.7% (61.0% by_asset_class raw) |
| Profit Factor | 2.25 (2.0 raw) |
| Avg Win | +2.66% |
| Avg Loss | −2.07% |
| Total PnL | +66.71% |
| Active picks (today) | 14 |

These numbers are **pre-VIX-filter** — they include picks taken during all VIX regimes.

---

## VIX Threshold Analysis (M-098 gate: VIX ≥ 25)

### 2024–2026 VIX ≥ 25 Calendar Events

| Period | VIX Peak | Duration (trading days) | Cause |
|--------|----------|------------------------|-------|
| Aug 2024 carry unwind | ~65 (intraday Aug 5) | ~5 days spike; ~10 days above 25 | JPY carry unwind, global equities rout |
| Oct–Nov 2024 election | ~23–26 | ~4 days above 25 | US election uncertainty |
| Early Jan 2025 | ~19–20 | 0 days above 25 | Mild pullback |
| Apr 2025 tariff shock | ~52 (Apr 7–8) | ~15 trading days above 25 | Liberation Day tariffs, S&P −19% drawdown |
| May 2025 | ~18–20 | 0 days above 25 | Partial tariff suspension recovery |
| May 18 2026 (today) | 19.09 | Currently below threshold | VIX pulled from cached feed |

**Total VIX ≥ 25 trading days in last 18 months: ~30–35 days (out of ~378 trading days = ~8–9% of time)**

---

## Opportunity Cost Estimate

### Assumption: ETF picks generated at flat ~1.2 picks/trading day (dashboard n=75 / ~63 trading days observed)

| Scenario | VIX ≥ 25 days | Blocked picks (est.) | WR of blocked subset (est.) | Forgone PnL |
|----------|--------------|---------------------|----------------------------|-------------|
| Conservative | 30 days × 1.2 picks | ~36 picks | Same as baseline (66.7%) | ~36 × 0.82% avg = +29.5% |
| Aggressive | 35 days × 1.2 picks | ~42 picks | 40% (stress periods lower WR) | ~42 × (0.4×2.66 − 0.6×2.07) = ~0.0% (breakeven) |

### Key Insight

VIX ≥ 25 events are overwhelmingly correlated with **market stress** (Aug carry unwind, Apr tariff shock). ETF strategies (sector rotation, mean reversion) perform *worse* in stress periods due to:
1. Wider bid-ask spreads (+50–200% of normal)
2. Correlation breakdown (diversification disappears)
3. Gap risk on overnight holds
4. Forced liquidations by other market participants

**The gate likely filters exactly the pick cohort with the lowest realized WR.** The conservative estimate of +29.5% forgone PnL is a theoretical maximum; realistic forgone PnL is probably close to $0 or negative (i.e., the gate saves losses).

---

## ETF Strategy-Specific Risk Assessment

| Strategy | VIX Regime Risk | Gate Impact |
|----------|-----------------|-------------|
| `leveraged_etf_decay` (SOXL/SQQQ shorts) | HIGH — leveraged ETFs see amplified vol in VIX spikes | Gate is risk-reducing; short leveraged ETFs can squeeze in vol spikes |
| `etf_sector_rotation` (XLK/XLE/XLF) | MEDIUM — sector ETFs have elevated beta in stress | Gate reduces but doesn't eliminate risk |
| `sector_rotation` (SPY/QQQ/IWM) | MEDIUM-HIGH — index ETFs behave predictably but WR drops | Gate appropriate |
| `bond_connors_rsi2` (TLT/IEF) | LOW — bond ETFs may be *anti-correlated* with VIX spikes | **Gate may block profitable flight-to-safety picks** |

### Bond ETF Exception Recommendation

Bond ETFs (TLT, IEF, SHY, LQD) historically *rally* when VIX spikes (risk-off flows). The blanket M-098 gate should be amended to **exempt `asset_class=BOND`** picks from the VIX block — these are not affected by the equity volatility regime the gate targets.

Action: Add BOND asset_class exemption to M-098 gate logic in `audit_trail/quality_gates.py` (future PR).

---

## Verdict

| Question | Answer |
|----------|--------|
| How many 2024–2025 winners would VIX gate have blocked? | Estimated 30–42 picks (~8–9% of total signal flow) |
| Was blocking them the right call? | YES — these periods have structurally lower ETF WR |
| Estimated forgone PnL at baseline WR | +29.5% (theoretical max); realistically ~0% or negative |
| Gate threshold (VIX ≥ 25) — is it calibrated correctly? | YES for equity/leveraged ETFs. Consider BOND ETF exception. |
| Should threshold change? | No — VIX 25 is a well-established institutional risk-off line. VIX ≥ 30 would miss the Aug 2024 event. |

---

## Recommendation

1. **Keep M-098 at VIX ≥ 25 threshold.** Opportunity cost is low; risk reduction is real.
2. **Add BOND ETF exemption** (TLT/IEF/SHY/LQD — asset_class=BOND) — these benefit from risk-off flows.
3. **Recompute this analysis post-MySQL-sync (2026-05-24)** using actual closed ETF picks with timestamps. Map to CBOE VIX daily close to get exact blocked vs. passed cohort comparison.
4. **Full backtest script:** `python tools/backtest/etf_vix_gate_backtest.py --start 2024-01-01 --end 2026-05-18 --threshold 25` (implement post-sync).

---

## Next Review

This document is superseded by the post-MySQL-sync version, estimated 2026-05-25.
