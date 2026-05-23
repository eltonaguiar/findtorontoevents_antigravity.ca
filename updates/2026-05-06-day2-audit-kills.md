# Day-1 + Day-2 Audit Kill Decisions (2026-05-06)

## Ground-Truth Source
Day-1 audit done against real `picks.recent_closed` / `alpha_engine/data/closed_picks.json` data.
Replaces all AI-fabricated performance numbers from prior swarm analysis.

## Real Performance (ground-truth)

| Tier | Strategy | WR | PF | n | Verdict |
|------|----------|----|----|---|---------|
| T1 KEEP | cftc_cot_commercial_signal | 73.3% | 3.97 | 45 | wire |
| T1 KEEP | cta_fx_multifactor | 69.2% | 11.15 | 13 | wire |
| T1 KEEP | fx_smart_forex_rsi2_mean_reversion | 64.3% | 5.96 | 14 | wire |
| T1 KEEP | stocks_rsi2_pullback | 56.4% | 1.31 | 39 | wire |
| T2 KEEP | cot_positioning | 50.0% | 3.51 | 24 | wire |
| T2 borderline | fx_smart_carry_trade_momentum | 43.3% | 1.66 | 30 | wire (PF≥1.5) |
| T2 borderline | cta_cross_asset_tsmom | 38.7% | 1.29 | 62 | wire (PF>1) |
| **KILL** | **combined_confidence** | 52.2% | 0.28 | 23 | wins-it-all-loses-it pattern |
| **KILL** | **forex_rsi2_mean_reversion** | 43.3% | 0.37 | 593 | large-n bleeder |
| **KILL** | **futures_momentum** | 41.6% | 0.56 | 539 | large-n bleeder |
| **KILL** | **cta_commodity_momentum_term** | 36.2% | 0.02 | 47 | total bleed — confirms SLV/USO cancel |
| **KILL** | **smart_money_accumulation** | 20.0% | 0.20 | 5 | structural loser |

## Changes Made (2026-05-06)

### audit_trail/quality_gates.py

**PERMANENTLY_KILLED_STRATEGIES** — 5 strategies added:
- `combined_confidence` (Day-2): 52.2% WR, PF 0.28, n=23 — wins-it-all-loses-it pattern
- `forex_rsi2_mean_reversion` (Day-2): 43.3% WR, PF 0.37, n=593 — large-n bleeder (was boosted in STRATEGY_SCORE_OVERRIDES)
- `futures_momentum` (Day-1 P1-E): 0% WR on 56 closed, PF 0.00 — KILLED 2026-05-06
- `cta_commodity_momentum_term` (Day-2): 36.2% WR, PF 0.02, n=47 — total bleed (confirms SLV/USO cancel)
- `smart_money_accumulation` (Day-2): 20.0% WR, PF 0.20, n=5 — structural loser

**STRATEGY_SCORE_OVERRIDES** — removed both boosts for forex_rsi2_mean_reversion:
- `+30` boost: commented out with KILLLED reason
- `+4` moderate boost: removed entirely

**SMART_PICKS_MIN_SCORE_FUTURES** — stale 6-line comment replaced with KILLED mention

**BLOCKED_STRATEGIES ONE winner comment** — updated from 'is the ONE winner' to 'was the ONE winner...now KILLED'

**BLOCKED_DIRECTION_TRIPLES** — 3 FOREX LONG blocks added:
- `FOREX + ig_contrarian_sentiment + LONG` (anti-edge long confirmed)
- `FOREX + myfxbook_retail_contrarian + LONG` (anti-edge long confirmed)
- `FOREX + quan_engine_swing + LONG` (anti-edge long confirmed)

### alpha_engine/smart_picks_engine.py

**BANNED_SYSTEMS** — added:
- `combined_confidence` (Day-2): wins-it-all-loses-it
- `forex_rsi2_mean_reversion`, `cta_commodity_momentum_term`, `smart_money_accumulation` (Day-2)

**Allowlist comments** — annotated `futures_momentum KILLED 2026-05-06` in commodity + futures allowlists

**Stale comment** — updated `NEW — futures_momentum` comment to mention KILLED

## Decisions NOT Made

### Dashboard nested stats fix (dashboard_generator.py)
Intended as a 1-file PR to populate nested strategy stats (`profit_factor`/`win_rate_pct`/`n`) for cta_replicator and forex_copy_trader substrats from `picks.recent_closed`.

**DECISION: SKIP** — The `collect_system_stats` loop's `_ensure_buckets` already creates strategy buckets on demand for every closed pick via `_track_pick_result_in_system`. The nested stats issue described in the audit was a phantom — `_build_strategy_breakdown` already gets populated stats for all strategies that appear in closed picks.

Additionally, the initially-attempted pre-aggregation approach would have double-counted closed pick stats (pre-aggregating wins/losses/flat/total_pnl, then the loop's `_track_pick_result_in_system` would add the same stats again). Reverted correctly.

**Action item**: If the `cta_replicator` tile still shows null stats for `cta_fx_multifactor` (69%/PF 11) after a fresh dashboard generation, reopen the ticket with a corrected fix.

## Resolved Audit Items

- [x] Kill 5 bleeders (add to PERM_KILLED + BANNED_SYSTEMS)
- [x] Remove forex_rsi2_mean_reversion score overrides
- [x] Update stale comment blocks (SMART_PICKS_MIN_SCORE_FUTURES, ONE winner)
- [x] Add 3 FOREX LONG blocks to BLOCKED_DIRECTION_TRIPLES
- [x] Document SLV/USO cancellation rationale (cta_commodity_momentum_term kill)
- [x] Verify resolver was working (not broken as swarm assumed)

## Open Items

- [ ] Verify cta_replicator tile shows `cta_fx_multifactor 69%/PF 11` after fresh dashboard generation
- [ ] Check if any live SLV/USO picks from cta_commodity_momentum_term need manual closure