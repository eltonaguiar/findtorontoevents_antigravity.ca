# 200-day MA trend strategy — verification + Monte-Carlo verdict (2026-05-29)

Independent check of the `/audit/ai_leaderboard.html` MA-trend strategies (`ma_strategy_leaderboard.json`).
Harness: `tools/backtest_ma_trend_montecarlo.py` (yfinance 6y, no-lookahead signal→t+1, 20bp, MC seed 20260529). NFA.

## Verdict: the high PF is REAL but it is NOT a standalone edge — it's a defensive overlay.

| Class | trade PF | Strat Sharpe | B&H Sharpe | Strat MaxDD | B&H MaxDD | MC timing p | read |
|-------|----------|--------------|------------|-------------|-----------|-------------|------|
| CRYPTO | 3.34 | 0.51 | 0.67 | 75% | 82% | 0.277 | underperforms B&H; no timing skill |
| EQUITY | 7.05 | 0.82 | 0.99 | 30% | 40% | 0.497 | underperforms B&H; no timing skill |
| ETF | 2.62 | 0.61 | 0.91 | 25% | 31% | 0.623 | underperforms B&H; no timing skill |
| COMMODITY | 2.04 | 0.47 | 0.87 | 43% | 33% | 0.601 | underperforms B&H (worse DD too) |
| FUTURES | 2.33 | 0.34 | 0.57 | 28% | 35% | 0.582 | underperforms B&H; no timing skill |
| FOREX | 0.89 | −0.02 | 0.32 | 16% | 22% | 0.668 | no edge |
| BOND | 0.55 | −0.10 | 0.04 | 16% | 26% | 0.647 | defensive only (lower DD), loses money |

### Why the leaderboard PF (EMA200 3.16 / CRYPTO 9.48) is misleading
- It's the **natural shape of trend-following** (high PF, low ~25–39% WR — a few big winners pay for many small losses).
- **Risk-adjusted it loses to buy-and-hold in every class** (Sharpe always lower).
- **Monte-Carlo timing test fails in all 7 classes** (p 0.28–0.67 ≫ 0.05): being long on above-MA days is statistically
  no better than holding the same number of *random* days → returns are **exposure, not timing skill.**

### The one genuine value
**Drawdown reduction** (MaxDD < buy-hold in 6/7 classes; e.g. CRYPTO 75% vs 82%, EQUITY 30% vs 40%, BOND 16% vs 26%).
So MA-200 belongs as a **regime/defensive overlay** (size down / de-risk when price < MA200), NOT as an alpha-generating pick source.

## Recommendation for /audit tracking
Track MA-200 picks under the audit data source **labeled honestly**: source `ma200_trend`, with the metric-honesty tier
🟡/🟠 and a note "trend-shape PF; no timing alpha (MC p>0.5); defensive overlay only — do not size as edge." Visible in the
funnel, gated out of active alpha picks. This prevents the leaderboard's PF from being misread as edge.
