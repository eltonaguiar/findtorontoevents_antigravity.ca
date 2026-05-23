# STRATEGY INVESTIGATION: quan_engine (C-005)

**Date:** 2026-05-18  
**Analyst:** Claude Code autonomous session  
**Scope:** quan_engine source system — all CRYPTO closed picks  
**Status:** Already BLOCKED. This report fulfills the investigation requirement.

---

## Executive Summary

**quan_engine is correctly and permanently blocked.** With n=5896, WR=30.4%, PF=0.41,
and total cumulative PnL of -995.61 (fractional), this is the worst source system
in the portfolio by absolute loss. No sub-strategy demonstrates positive edge.

**Recommendation: Keep BLOCKED. Scheduled autopsy remains 2026-05-24.**

---

## Data Summary (all-time, closed_picks.json)

| Metric | Value | Assessment |
|--------|-------|------------|
| Win Rate | 30.4% | FAIL — below 50% baseline |
| Profit Factor | 0.41 | FAIL — every $1 wins $0.41 |
| Total n | 5,896 | High confidence — not noise |
| Total PnL | -995.61 | Cumulative -99,561% loss |
| Block status | BLOCKED (L1406 quality_gates.py) | Correct |

---

## Sub-strategy Breakdown

| Strategy | n | WR | Avg PnL/trade | Block Status |
|----------|---|----|---------------|--------------|
| quan_engine_scalp | 5,293 | 30% | -18.14% | BLOCKED |
| unknown | 468 | 38% | -7.32% | (via parent block) |
| quan_engine_swing | 109 | 28% | -0.009% | BLOCKED |
| quan_engine_position | 26 | 0% | -4.14% | BLOCKED |

**No sub-strategy has positive expected value.**

---

## Alpha Decay Analysis

| Symbol | n | WR | Avg PnL | Interpretation |
|--------|---|----|---------|----------------|
| MATICUSDT | 1,057 | 0% | -15.00% | Complete loss of alpha — 0 wins |
| BTCUSDT | 655 | 34% | -15.96% | Negative edge on BTC — contrary signal |
| KASUSDT | 634 | 41% | -9.77% | Near-random WR but wrong direction |
| TAOUSDT | 631 | 36% | -16.71% | Deep negative edge |
| HYPEUSDT | 553 | 42% | -22.31% | Large losses per trade |
| TRXUSDT | 245 | 49% | -1.82% | Near-break-even only |

**Conclusion:** quan_engine signal is the inverse of a good signal on high-volume CRYPTO
pairs. MATICUSDT 0% WR on n=1,057 is statistically indistinguishable from a
pure contrarian signal. No pair shows consistent positive alpha.

---

## Root Cause Hypothesis

Based on the data pattern:
1. **Stale signal logic**: quan_engine appears to be a momentum-following system
   that was calibrated on 2021-2022 bull market data. In the current market
   (2025-2026), momentum signals reverse-decay within the signal window.
2. **Execution timing**: quan_engine_scalp avg loss of -18% suggests SL is hit
   consistently before any TP. The signal may be directionally correct but with
   insufficient TP/SL ratio for volatile CRYPTO.
3. **Correlation regime**: Since the M-037 report (2026-05-17), correlation regime
   is ELEVATED (sleeve_scalar=0.555). Correlated signals from quan_engine fire
   simultaneously and compound losses.

---

## Decision

**Block maintained. No further action required until scheduled autopsy 2026-05-24.**

The autopsy should focus on:
1. Whether quan_engine signal source is still actively generating new picks
2. If signal generation has stopped, formally archive the module
3. Whether `macd_crossover` strategy (also used by rapid_fire) can be extracted
   and tested independently

---

## Related Items
- `quan_engine_scalp` block: `audit_trail/quality_gates.py` L1401
- `quan_engine` block: `audit_trail/quality_gates.py` L1406
- `quan_engine_position` block: `audit_trail/quality_gates.py` L1407
- Scheduled autopsy: 2026-05-24 (MASTER_ACTION_PLAN comment)
- rapid_fire investigation: `reports/rapid_fire_strategy_investigation_2026-05-18.md`
