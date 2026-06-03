# ETF Dual-Momentum — FIRST sleeve to clear the gate-stack (2026-06-03)

Built per the swarm-endorsed track (reject broken-ledger re-audit → new archetype on CLEAN daily bars).
`verified_strategies/etf_dual_momentum_backtest.py`. Textbook dual-momentum (Antonacci): monthly,
absolute filter (beat cash BIL) + relative rank (top-1 of SPY/QQQ/EFA/AGG/GLD). Walk-forward by
construction (each month uses only trailing 12m). Real daily closes via data_fetcher (yfinance), 48
months. Fixed textbook params (lookback=12, top_k=1) — not fit, low overfit risk.

## Result (live, real data)
| Metric | Value | Bar | Pass? |
|---|---|---|---|
| Profit factor | **3.57** | ≥1.5 | ✅ |
| Sharpe (annual) | **1.62** | ≥1.0 | ✅ |
| Win rate (monthly) | 72.9% | — | ✅ |
| Max drawdown | **−12.4%** | ≤20% | ✅ |
| CAGR | 29.1% | — | — |
| **#111 attribution vs SPY** | alpha 1.7%/mo, **t=2.36**, IR 0.37, beta 0.34 | t≥2.0 & IR≥0.10 | ✅ |
| **Bootstrap PF 95% CI** | **[1.64, 9.69]** | lower>1.0 | ✅ |
| Cost robustness | PF 3.20 / Sharpe 1.48 @ 20bps/mo | — | ✅ |

## Why this matters
This is the **first candidate in the session to clear the whole gate-stack**: attribution (#111),
bootstrap-CI (#481), cost-robustness, Sharpe>1, MDD<20%. Crucially its alpha is **real** —
market_beta only 0.34 and t=2.36, so it is NOT just riding SPY (contrast: tournament deepseek_v4
FAILED attribution at t=1.74). And it sidesteps every flaw the cross-review flagged: clean daily
bars (no batch-stamp), real-market benchmark (not crowd-proxy), walk-forward (not circular).

## Honest caveats (NOT yet real-money-ready)
- Single 48-month full-sample run; no purged-embargoed CV or explicit OOS holdout (mitigant: fixed
  textbook params, inherently walk-forward → low overfit, but not zero).
- 48 monthly observations is a modest sample for a Sharpe claim.
- ETF universe is small (5 risk assets); survivorship of the chosen tickers is benign but noted.

## Next steps (forward, per #66/#67)
1. Pre-register the hypothesis (M-107) before any further tuning.
2. Forward shadow-size at ≤0.5% via the #67 ladder; require 2× 4-week windows within ±10% of this
   backtest PF before sizing up.
3. Add purged-embargoed walk-forward CV (#66 harness) + regime split as confirmation.
4. This is a promotion CANDIDATE, not a promotion. money_ready stays []; this earns a forward slot.

## Reproduce
`python3 verified_strategies/etf_dual_momentum_backtest.py`
