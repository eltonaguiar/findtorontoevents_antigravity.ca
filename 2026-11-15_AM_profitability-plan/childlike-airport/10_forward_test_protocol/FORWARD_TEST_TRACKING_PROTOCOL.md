# 10 — Forward-Test Tracking Protocol (Easy, Fast-Kill vs Hold)

**Goal:** convert backtest/simulation candidates into *forward* evidence quickly, eliminate bad strategies fast, and hold only what can plausibly beat its benchmark net of costs.

## 0. Principles
- **Forward/paper only first** (live marks, no capital) until gates pass.
- **Pre-register** before first trade: hypothesis, universe, rules, params, costs, benchmark, horizon, kill/hold/promote thresholds.
- **Benchmark-relative:** equity/ETF vs SPY/total-market (total return) risk-matched; cash hurdle T-bills/SGOV-like; allocation vs matched blend. Beating 0% is not enough.
- **Net-of-all-costs** and realistic fills (intrabar/next-bar/gap-aware, or NAV/next-NAV for funds). Log slippage vs model.

## 1. Strategy card (one per sleeve, required)
| Field | Value |
|---|---|
| Strategy ID / version | |
| Asset class & universe | |
| Style / holding period | long-term / swing / position / intraday (justify) |
| Benchmark / hurdle | |
| Entry/exit/risk rules (exact) | |
| Expected trades per month | |
| Costs model (fees, spread, slippage, funding/roll/borrow) | |
| Max risk/trade, max exposure, DD limits | |
| Start date (forward) & review dates | |
| Owner / worktree | |

## 2. Decision windows (time-boxed, to avoid limbo)

| Horizon bucket | Typical hold | Min evidence before decision | Primary decision |
|---|---|---|---|
| **H0 – Sanity (fast kill)** | any | 5–10 trades **or** 5 trading days | kill obvious breaks (data/fill/logic/slippage) |
| **H1 – Short-horizon** | intraday–few days | 10–20 trades **and** ≥2 weeks | **FAST KILL** if offside; else hold to H2 |
| **H2 – Swing** | days–weeks | 20–40 trades **and** ≥6–8 weeks | kill/hold/promote-to-paper-scale |
| **H3 – Position/TAA** | weeks–months | 30–60 trades **or** ≥3 months (rebalance strategies: ≥3–6 rebalances) | hold vs kill; needs regime coverage |
| **H4 – Long-term allocation** | months–years | ≥6–12 months tracking (and/or ≥4 quarterly reviews) | allocation suitability vs benchmark |

*Use the bucket matching the strategy’s design. Do not judge a monthly-rebalance/TAA sleeve on 1 week of noise, and do not let a failing short-horizon sleeve linger for months.*

## 3. Fast-kill rules (eliminate early, deterministic)
Trigger **KILL** (stop forward test, log postmortem) if any holds at the first eligible checkpoint:

- **Data/fill invalid:** unresolved 0%/blank/stale marks, look-ahead/leakage, unexplainable PnL reconciliation error, or realized slippage/fill behavior materially worse than modeled with no fix.
- **Expectancy broken:** net expectancy ≤ 0 after costs on closed trades (min sample for bucket) **or** PF_net < 1.0.
- **Benchmark failure (active):** trailing net return and/or risk-adjusted return clearly below benchmark/buy-and-hold for the bucket (not a single-day blip) without offsetting risk reduction.
- **Risk breach:** realized MDD or daily/weekly loss exceeds pre-set limit; concentration or exposure breach.
- **Process failure:** cannot execute rules consistently; signals non-reproducible.

**FAST KILL applies immediately** to H0/H1 strategies meeting the above; do not “wait for significance” when economics are negative.

## 4. Hold / continue rules (needs more time)
Mark **HOLD** only when: (a) no kill trigger fired, (b) sample/time insufficient for the design horizon, (c) metrics are noisy but not decisively negative, and (d) execution/data are clean. Set a **next decision date** and required sample — no indefinite holds.

## 5. Promote-to-paper-scale / promote-candidate rules
Consider **PROMOTE (paper-scale / candidate)** only when, on the trusted forward sample for its horizon:
- Net expectancy > 0 and PF_net ≥ 1.2 (≥1.5 preferred) with stable rolling behavior.
- Meets/exceeds benchmark on net, risk-adjusted basis (or delivers justified lower-DD profile for allocation).
- Risk within limits (MDD, CVaR, concentration) and realized costs/slippage within model.
- Sufficient trades/time for bucket (and moving toward n≥100; ≥500 preferred for noisy classes) with no integrity flags.

> Still **not** live-capital-ready until full repo gates pass (effective-N/DSR/PBO, regime stability, independent reproduction).

## 6. Easy tracking sheet (weekly 10-minute update)

Use `tracker_template.csv` (one row per strategy per review). Minimum fields:

| Column | Meaning |
|---|---|
| `review_date_utc` | review timestamp |
| `strategy_id` | stable id/version |
| `asset_class` | CRYPTO/EQUITY/ETF/MF/BOND/FOREX/COMMODITY/FUTURES/PM |
| `horizon_bucket` | H0/H1/H2/H3/H4 |
| `start_date` | forward start |
| `trades_closed` / `trades_open` | counts |
| `win_rate` | closed |
| `pf_net` | net profit factor |
| `expectancy_net` | per trade or % |
| `return_net` | period return net |
| `benchmark_return` | same period |
| `excess_vs_benchmark` | net − benchmark |
| `sharpe_or_sortino` | if enough data, else blank |
| `max_dd` | realized |
| `avg_slippage_bps` | realized vs model |
| `data_integrity_flags` | 0%/blank/stale/leak/fill issues |
| `kill_trigger` | Y/N + reason |
| `status` | FAST_KILL / HOLD / PROMOTE_PAPER / KILLED |
| `next_review_date` | required if HOLD |
| `notes` | 1 line |

## 7. Weekly review cadence (lightweight)
1. Update rows for all active sleeves (10 min).
2. Apply **kill triggers first** → mark FAST_KILL/KILLED immediately.
3. For HOLD, confirm time/sample still insufficient and set next review.
4. Compare active/trend candidates vs **buy-and-hold benchmark** every review.
5. Roll up: count FAST_KILL vs HOLD vs PROMOTE_PAPER; reallocate effort to top 1–2 and the beta baseline.

## 8. Classification cheat-sheet
- **FAST KILL:** negative net expectancy/PF<1, broken data/fills, risk breach, or clearly lagging benchmark at eligible checkpoint.
- **HOLD LONGER:** clean execution, no kill trigger, but horizon/sample not reached (especially H3/H4 allocation/TAA).
- **PROMOTE (paper):** net positive, benchmark-competitive risk-adjusted, within risk/cost model, sufficient forward evidence for its horizon.

## 9. Simulation-informed priors (to set expectations)
Model-based sims (`../09_backtest_simulations/`) suggest low-cost diversified/balanced approaches can achieve favorable P(>0) and drawdown profiles, while **marginal gross edges often turn net-negative after 10–30bps RT costs**. Treat this as prior, not proof: validate on trusted historical data and forward marks.
