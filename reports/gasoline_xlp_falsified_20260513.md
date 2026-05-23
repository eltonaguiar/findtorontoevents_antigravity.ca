# Gasoline → XLP/XLY lag hypothesis — FALSIFIED

**Date:** 2026-05-13
**Tool:** `tools/backtest_gasoline_xlp_lag.py`
**Swarm projection (4/4 engines):** Gasoline (RB=F) leads XLP/XLY by 5-15 days, Sharpe ~1.1
**Actual:** Cross-correlation peak at lag=0 (contemporaneous, 0.19), all rotation variants negative Sharpe

## Cross-correlation summary

Peak XLP corr at lag 0 = +0.191. Peak XLY corr at lag 0 = +0.213. Beyond lag 2 days, correlation collapses to noise (-0.03 to +0.03).

## Rotation backtest

12 variants tested (threshold × hold). Best variant (RB 5d > 5%, hold 5d): PF 0.98, Sharpe -0.03 = NO EDGE. All other variants worse.

## Swarm-projection track record (cumulative)

| Strategy | Projected | Actual | Verdict |
|---|---|---|---|
| EQUITY VIX<20 | Sharpe 1.45 | Sharpe 2.19 | EXCEEDED |
| EQUITY VIX<22 | Sharpe 1.45 | Sharpe 1.98 | EXCEEDED |
| BOND credit-spread | Sharpe 1.0+ | Sharpe 0.58 | FALSIFIED |
| BOND duration rotation | Sharpe 1.0+ | Sharpe 0.36 | FALSIFIED |
| Diwali GLD seasonal | (no projection) | PF 1.98, no alpha | mixed |
| Gasoline → XLP rotation | Sharpe 1.1 | Sharpe -0.03 | FALSIFIED |

**3 of 6 exceed projection. 3 of 6 falsified. 50% hit rate.**

## Pattern

- Regime-GATE projections (skip when bad): **WORK** (VIX)
- Lead-LAG projections (X leads Y by N days): **FAIL** (gasoline, credit spread, duration)

Hypothesis: markets pre-discount cross-asset economic mechanisms within hours. Daily-frequency lead-lag signals are noise.

## Methodology update

Any "X leads Y by N days" swarm claim REQUIRES cross-correlation matrix backtest BEFORE accepting as actionable.

NFA.
