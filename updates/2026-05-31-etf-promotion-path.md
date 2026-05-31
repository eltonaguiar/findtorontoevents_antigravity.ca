# ETF Strategy Promotion Path — Probation to Live

**Date:** 2026-05-31
**Incident:** INCIDENT_ETFS #1 (P2)
**Status:** Documentation — defines graduation criteria for the 10+ ETF strategies currently on probation with zero verified forward trades.

## Current State (2026-05-31)

Per `trading_picks` (ejaguiar1_stocks), `category='etf'`:

| Strategy | Emitted | Closed | Status |
|---|---|---|---|
| `leveraged_etf_decay` | 69 | 0 | Probation |
| `etf_rsi2_pullback` | 57 | 0 | Probation |
| `etf_faber_tactical` | 37 | 0 | **Probation — graduation candidate** |
| `etf_sector_momentum` | 33 | 0 | Probation |
| `etf_dual_momentum` | 22 | 0 | Probation |
| `etf_cross_sectional_momentum` | 18 | 0 | Probation |
| `etf_risk_parity_rotation` | 12 | 0 | Probation |
| `sector_rotation_etf` | 9 | 0 | Probation |
| `etf_sector_dual_momentum` | 8 | 0 | Probation |
| `etf_trend_following` | 5 | 0 | Probation |

Total etf-category emissions: ~320. **Total closed: 0.** Asset-class verdict in `money_ready_verdict.json` is INSUFF-N (PF 11.99 / WR 50% on the 2 closes that exist, neither tagged to an ETF strategy).

## Why etf_faber_tactical Is the Graduation Candidate

Per Ring 2.6 1T peer review (2026-05-31) and on-disk citation at `alpha_engine/etf_strategies.py:498-523`:

### 1. Source Academic Backing

**Faber, M. (2007, updated 2013/2020) — "A Quantitative Approach to Tactical Asset Allocation"** (Journal of Wealth Management).

Canonical binary-state TAA rule: hold the asset when Close > 10-month SMA, otherwise cash. Replicated across decades and asset classes.

**Published edge (Faber 2013 update, 1973–2012 backtest):**
- Sharpe ~0.76 vs SPY ~0.43
- Max drawdown ~-17% vs SPY ~-51%
- Avg-win / avg-loss ratio ~2.3
- Profit factor ~1.4
- Per-trade WR ~45%

Universe (per Faber's original 5-asset GTAA): SPY, QQQ, EFA, IEF, GLD — already coded at `alpha_engine/etf_strategies.py:529`.

### 2. Wire-Up Status — Verified Intact

Routing for ETF mirrors the EQUITY bridge fix (INCIDENT_STOCKS #3 resolution). Confirmed live 2026-05-31:

- `alpha_engine/scanner.py:292` — `from etf_strategies import ETF_STRATEGIES`
- `alpha_engine/scanner.py:2106` — loaded into the dispatch dict when `strategy_filter in ("all", "etf")`
- `alpha_engine/etf_strategies.py:979` — `"etf_faber_tactical": etf_faber_tactical` registered in `ETF_STRATEGIES`
- `alpha_engine/outcome_resolver.py:2498-2524` (M-113, 2026-05-18) — ETF scanner output files added to `resolve_active_non_crypto()` source list

The fact that 37 `etf_faber_tactical` picks landed in `trading_picks` proves emission and routing work. The 0-closed problem is a **resolver-side closure-write gap**: picks reach the DB as ACTIVE but the resolver doesn't push the closed-state back. Tracked separately (open follow-up; see INCIDENT_FOREX #7 resolver bug class for the same pattern).

### 3. Required Forward Floor for Graduation

For `etf_faber_tactical` (or any ETF strategy) to leave probation and qualify for sizing decisions, it must clear ALL of the following on real forward data (no backtest, no replay):

| Gate | Threshold | Rationale |
|---|---|---|
| **n_closed** | ≥ 30 monthly observations (~30 closed picks across the 5-asset universe) | Faber TAA is monthly-bar; 30 obs = ~30 months single-asset or ~6 months × 5 assets |
| **Max drawdown** | < 15% peak-to-trough | Faber's published MDD is ~17%; require tighter to credit live discipline |
| **Avg monthly return** | > 0 (positive) | Minimum bar; "alive" |
| **Profit Factor** | ≥ 1.20 (Tier-3 floor) | Published PF is ~1.4; allow 0.2 slippage for live frictions |
| **WR** | ≥ 40% | Published per-trade WR is ~45%; 5pp tolerance |
| **Sharpe (annualized)** | ≥ 0.50 | Published Sharpe is ~0.76; ~33% slippage tolerance |
| **No concentration violation** | HHI < 0.30 across the 5-asset universe | Per `feedback-concentration-strategy-not-engine.md`: single-symbol concentration kills classification; Faber's 5-asset universe must show actual diversification, not 90% SPY |

Numbers must come from `trading_picks` filtered to `strategy='etf_faber_tactical' AND status='CLOSED' AND created_at >= <graduation_window_start>`. Pre-graduation cohort is **not** retroactive — only post-fix forward closes count.

### 4. Probation → Live Promotion Process

**Phase 1 — Resolver fix (prerequisite, blocks all 10 strategies):**
- Diagnose why 0 ETF picks are reaching CLOSED state despite M-113 source-list patch
- File: `alpha_engine/outcome_resolver.py` — likely the `resolve_active_non_crypto()` writer isn't matching ETF rows back to `trading_picks` (vs only writing `closed_picks.json`)
- Owner: same agent fixing INCIDENT_FOREX #7
- Acceptance: at least one ETF pick transitions ACTIVE → CLOSED in `trading_picks` within 7 days of the next pick generation cycle

**Phase 2 — Forward floor accumulation (per strategy):**
- Strategy stays in probation; picks emit but receive `confidence_cap = 0.55` and `position_size_multiplier = 0.5` until graduation
- Run for ≥ 30 monthly observations
- Weekly: re-run `python3 tools/strategy_tier_tracker.py` and snapshot the strategy row

**Phase 3 — Graduation review:**
- Compute the 7-gate matrix above on the live cohort
- If ALL pass: file PR `graduate(etf_faber_tactical) → live`, removing the confidence cap and size multiplier
- If ANY fail: stay in probation, re-evaluate at next 30-obs milestone
- If max drawdown breached (>15%) or n>30 with PF<1: demote per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` + `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (export → mutate → test before kill)

**Phase 4 — Live monitoring:**
- Post-graduation, strategy is monitored against the same 7 gates on a rolling 60-pick window
- Drawdown breach (>15% peak-to-trough) → automatic demotion to probation, no debate
- WR or PF dropping below floor for 30 consecutive picks → mutation-before-kill protocol

## Other Strategies — Same Path

The same 7-gate floor applies to the other 9 ETF strategies (`etf_dual_momentum`, `etf_sector_momentum`, etc.). Each must independently clear n≥30 + MDD<15% + PF≥1.20 to graduate. No batch promotions.

`leveraged_etf_decay` has a special caveat: it's a short-volatility decay-capture trade. Its theoretical edge is fee/contango-driven, not trend-driven. Forward floor for that strategy should add a **max-position-duration < 30 days** gate (leveraged ETFs are not buy-and-hold instruments) and a **VIX-regime filter** (only emit when VIX < 25, per `alpha_engine/scanner.py:2619` VIX confidence adjustment block).

## What This Doc Does NOT Do

- Does not change code
- Does not graduate any strategy today (all stay probation)
- Does not unblock the resolver — that's tracked separately
- Does not retroactively credit any pre-2026-05-31 closes (there are none anyway)

## References

- `alpha_engine/etf_strategies.py:498-600` — Faber TAA implementation
- `alpha_engine/scanner.py:292,2106` — ETF routing wire-up
- `alpha_engine/outcome_resolver.py:2498-2524` — M-113 ETF pick files in resolver
- `money_ready_verdict.json` 2026-05-24 — ETF INSUFF-N (PF 11.99 / WR 50% / n=2)
- `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` — kill protocol if probation fails
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md` — mutate-before-kill axis
- `reports/peer_blackbox_incidents-enhancements-pr_2026-05-31.md` — INCIDENT_ETFS #1 source
- Faber, M. (2007). "A Quantitative Approach to Tactical Asset Allocation." Journal of Wealth Management.
