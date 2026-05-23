# 2026-05-18 Real Money Readiness Audit

## Executive Summary
Current trading audit system shows mixed readiness for real-money deployment. Core strategies (chatgpt_combined Tier A) demonstrate 75-83% historical WR but require strict risk controls due to recent DB inconsistencies and strategy drift detection gaps.

## Key Findings
- **chatgpt_combined**: Rated Tier A (ship-ready). 75-83% WR historically. Data at battleground/data/chatgpt_combined_signals.json. Strong candidate for real money with position sizing limits.
- **Asset Class Performance**: Forex threshold ±0.0005% vs CRYPTO ±5%+. Recent examples: WIF +12.67%, TURBO +12.06%. Significant variance requires dynamic thresholds.
- **Database Health**: Critical issues identified:
  - 57,710 NULL closed_at rows in trading_picks (orphan records).
  - ejaguiar1_stocks (14GB) is primary for /audit FWD WR%, Track%.
  - ejaguiar1_sportsbet and ejaguiar1_memecoin largely stale/abandoned.
- **Active Picks**: active_picks.json confirmed EMPTY (2 bytes). No live positions detected.
- **Audit Gaps**: Previous "audit-daily" suite created but universal_pick_resolver shows 92% UNKNOWN asset_class in some batches (fixed 2026-05-04).

## Risk Assessment
- **High Risk**: Orphaned DB rows and lack of automated cleanup could lead to incorrect performance metrics.
- **Medium Risk**: Reliance on free-tier models (tencent/hy3-preview:free) for swarm analysis introduces potential instability.
- **Low Risk**: Core prediction engine stable per recent ruflo swarm integrations.

## Recommendations for Real Money
1. Implement mandatory DB safety protocol: Archive to ejaguiar1_backups before any modifications.
2. Enforce 8+ picks minimum for statistical edge validation.
3. Add rolling window performance tracking (3-day, 7-day) per asset class.
4. Deploy with paper trading first for 7-14 days before live capital.
5. Monitor via /audit dashboard with real-time MySQL sync.

## Verification Steps
- Run `python3 tools/SWARM/swarm_history.py` to confirm recent swarm runs.
- Check active_picks.json size and content.
- Validate no NULL closed_at via safe SQL queries.

**Status**: CONDITIONAL GO for real money with safeguards. Not yet "fire and forget".

Generated: 2026-05-18 by Grok agent fix
Canonical path: /mnt/e/findtorontoevents_antigravity.ca/updates/2026-05-18-real-money-readiness-audit.md
## 2026-05-18 Autonomous Harness Update (Claude session)
- Ran edge_stability_harness simulation on policy-clean pf_registry.
- Result: Only 10 admissible cohorts (all CRYPTO ml_enhanced_* with PF>=1.5, n>=20, WR>=50%).
- 249 cohorts killed (low n / low PF / poor WR).
- Action: Paper-trade only the 10 admissible CRYPTO cohorts with disagreement (>=3 sources) + kill-switch.
- All other asset classes blocked until new data.

Generated with autonomous execution.
