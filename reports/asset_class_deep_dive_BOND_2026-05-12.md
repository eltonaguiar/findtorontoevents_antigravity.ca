# BOND Asset-Class Deep-Dive — 2026-05-12

Investigator `abda5867be22509f3` output. BOND meets PF (1.72) + WR
(55.6%) floors but n=18 is far below charter 100. Scanner exists at
`alpha_engine/bond_scanner.py` with 3 strategies; registry wired this
session (commit `5c7a8c43a27`).

## Critical finding — FRED API timeouts kill emission

**The 18 BOND picks visible on /audit are LEGACY.** The active emitter
`tools/bond_emitter_spike.py` has been producing **0 picks per run** since
~2026-04-20 due to FRED API timeouts on every yield-curve series fetch
(DGS2, DGS10, DGS30, T10Y2Y, etc.).

- Workflow `.github/workflows/alpha-engine-bond.yml` runs daily at 06:10 UTC; last 5 runs (May 7-11) all succeeded.
- But the emitter writes an empty array because FRED times out.
- yfinance fallback exists but emits 0 picks too.
- → BOND scanner is **silently dead**; the 18 live picks are pre-May-05 orphans.

**Fix priority:** unblock FRED before any BOND ramp work. Likely requires:
- `FRED_API_KEY` env var refresh (memory: integration ranks #4 with note "exists, just needs API key")
- OR fallback endpoint via FRED's public CSV endpoints
- OR yfinance-only mode for the May ramp window

## BOND scanner architecture (`bond_strategies.py`)

3 strategies, all RR-gated at ≥1.20, all with 4% SL / 6% TP caps (low-vol bond tuning):

1. **bond_yield_momentum** — SMA20/50 crossover + RSI(14), fires on trend fresh/strong (bars_since_cross ≤5 or RSI >60/<40). Fires BUY or SELL.
2. **bond_duration_rotation** — TLT SMA50 vs SMA200 regime filter; rotates between long/short duration buckets; fires 1 pick per regime.
3. **bond_mean_reversion** — Bollinger Band (20,2) overbought/oversold + volume ratio >1.2. Targets mid-band TP.

All 3 are conventional Treasury/duration-aware logic — solid foundation.

## External-model candidates

| Library | Verdict |
|---|---|
| **robertmartin8/PyPortfolioOpt** | Black-Litterman + HRP over duration spectrum. Excellent for portfolio-level allocation. Requires covariance matrices + benchmark construction (new work). |
| **QuantConnect/Lean** | /Algorithms has yield-curve strategies (slope steepener/flattener); directly integrable. Slow-loop backtest overhead. |
| **chen-luo/bond-portfolio-optimization** | Constrained optimization focus; lacks real-time signal generation. Offline rebalancing only. |
| **PIMCO research blog** | Academic + practical (duration-momentum, slope-of-curve, breakeven inflation). Reference material, no code library. |

**Verdict:** Integrate QuantConnect/Lean slope-trades if cron can execute 1d lookback. Skip portfolio-level libs (orphan risk under CLAUDE.md Wire-Up Rule).

## 5-step plan to reach n≥100

- **Step A** — Fix FRED timeout (API key refresh, fallback endpoint, or yfinance-only mode for May ramp). **This is the blocking item.**
- **Step B** — Verify `bond_emitter_spike.py` re-runs daily, inspect `active_picks_bond.json` output (confirm >0 picks landing).
- **Step C** — Add 2 new strategies:
  - Yield-curve slope flattener (TLT-IEF spread momentum)
  - Credit-spread mean reversion (LQD-AGG OAS proxy)
- **Step D** — Weekly audit (May 12-19): watch pick count, WR%, PF trend (target WR≥50%, PF≥1.50 by May 26).
- **Step E** — Once n≥100 clean trades, promote BOND to SHADOW-candidate for next class-deviation review.

## Expected impact on /audit

- **Immediate (Step A):** unblock FRED → bond_emitter resumes; expect 5-10 picks/week.
- **30 days:** BOND n: 18 → 50+ if emitter restored + 2 new strategies live.
- **60 days:** n=100 reachable; BOND becomes T2-stable on the dashboard.

## Refs

- `alpha_engine/bond_scanner.py` (entry-point)
- `alpha_engine/bond_strategies.py` (3 strategies)
- `tools/bond_emitter_spike.py` (cron emitter — FRED-blocked)
- `.github/workflows/alpha-engine-bond.yml`
- `alpha_engine/config.py:721` (14 BOND symbols)
- `audit_trail/dashboard_generator.py:3897+` (registry, wired this session)
- Investigator `abda5867be22509f3` 2026-05-12

## NFA

Research surface only. BOND ramp gated on FRED fix. Until FRED works, the
registry add from commit `5c7a8c43a27` is dormant.
