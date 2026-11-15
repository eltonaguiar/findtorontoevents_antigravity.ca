# PRE_PROMPT.MD

**Core statistical and risk measures that must be beaten (common to all asset classes)**

These are the minimum set that survives investor scrutiny. Thresholds below are practical starting bars for a research system; raise them for larger capital.

### Must-pass metrics (compute net of all costs)
| Metric | Backtest minimum | Forward-test minimum | Why it matters |
|--------|------------------|----------------------|---------------|
| Expectancy per trade | > 0 after costs | > 0 and stable | Absolute edge |
| Profit factor | ≥ 1.3 | ≥ 1.2 | Gross wins / gross losses |
| Sharpe (annualized) | ≥ 0.7 (deflated) | ≥ 0.5 realized | Risk-adjusted return |
| Sortino | ≥ 1.0 | ≥ 0.7 | Downside risk |
| Calmar / Sterling | ≥ 0.4 | ≥ 0.3 | Return / max drawdown |
| Max drawdown | ≤ 20–25% | ≤ same or better | Capital preservation |
| Win rate + payoff | Win ≥ 40% or payoff ≥ 1.8 | Same direction | Consistency of edge |
| Bootstrap CI on mean excess return | Excludes 0 at 95% | Same | Statistical significance |
| t-stat on returns | ≥ 2.0 | ≥ 1.5–2.0 | |
| Deflated Sharpe / White’s Reality Check | p < 0.05 after all trials | n/a (already corrected) | Multiple-testing control |
| Walk-forward efficiency | ≥ 50–60% | n/a | Parameter stability |
| Monte Carlo (block bootstrap) | ≥ 70% of paths positive; 5th-percentile not catastrophic | Same on realized trades | Path dependence / luck |
| Regime robustness | Positive expectancy in ≥ 3 of 4 regimes (bull/bear/sideways/high-vol) | Same | Not a single-regime artifact |
| Shuffle control | Shuffled prices do **not** reproduce edge | n/a | No look-ahead / leakage |

Risk-management methods that must be present and validated:
- Explicit position sizing (fixed fractional, volatility targeting, or Kelly fraction ≤ 0.25)
- Hard stop or ATR-based stop + take-profit (or time-based exit)
- Portfolio-level constraints (max concentration, max sector/asset-class exposure, correlation cap)
- Full friction model (spread + commission + slippage + funding/borrow + taxes)
- Drawdown circuit breakers

### Backtest requirements (all asset classes)
- Strict chronological train / test / walk-forward (no future data in features)
- Rolling recalibration
- Full cost model specific to the asset class
- Multiple-testing correction using the project-wide trial count (you already have ~871 strategies)
- Reproducible code + fixed seeds + versioned data
- Control experiments (permuted prices)

### Forward-test requirements (all asset classes)
- Pre-registered before any live/paper results are known (rules, universe, parameters, TP/SL, sizing frozen)
- Minimum independent trades: 60 for significance; 100+ preferred
- Same metrics as backtest, computed only on the forward window
- Public or internal audit trail (timestamped picks → outcomes)
- Decision thresholds declared in advance (e.g., “kill if 90-day Sharpe < 0 after 40 trades”)

### Asset-class specific adjustments
(See full table in user prompt for stocks, ETFs, crypto, forex, bonds, commodities, mutual funds.)

### Ideal operational setup for daily picks → database
(See full recommended flow in user prompt: daily JSON emission → weekly ingestion → resolver → audit dashboard.)

**Context from past 24-48 hours (WIRED_IN, ALL_STRATEGIES.md, profitability plans, money_ready_verdict.json, latest commits):**
- No asset class is currently MONEY_READY (0/9 classes pass full gates; CRYPTO PF ~0.92, EQUITY ~0.94, thin ETF samples).
- wired_in_childlike is paper-only shadow monitoring (`wired_in_trend_momo_4d` for ETF/equity, `wired_in_short_duration_ballast` for bonds; PF 1.02–1.06 on replay, fails PF≥1.5, benchmark beat, DSR, PBO, SPA, walk-forward).
- Extensive inventory (700+ strategies across baby, alpha_engine, world_class_v21 institutional, ml_enhanced, regime, momentum, HMM, stat-arb, mutation engine).
- Strongest historical signals (94% WR on FETUSDT ml_enhanced, 70-81% on equity pilots) not yet proven forward.
- Today's commits added quant prompt kits, negative-result ladders, per-asset profitability plans, simulation results, forward_tracker, benchmark ledger proof.
- Deployment convention: WIRED_IN/final_v001/<datetime>_<worktreename> with PRE_PROMPT.MD, ALGORITHM_SPEC, justification, research/backtest, elimination, JSON artifacts, audit integration notes.
- Standing goal: Find and prove statistically valid profitable approach per asset class that beats benchmark after costs, passes all gates, feeds audit dashboard with green MONEY_READY tiles.

This PRE_PROMPT captures the exact user directive and synthesized context for the finalized strategy work in this folder.