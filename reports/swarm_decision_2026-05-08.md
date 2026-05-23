# Swarm Decision — Cross-Doc Top-7 Action Plan 2026-05-08

3-engine swarm (deepseek + cerebras + gemini) ranked top-7 across 4 proposal docs.
Kilo timed out (>5 min); proceed w/ 3-of-4 consensus.

## "If only one could ship today" — 4-engine split

| engine | pick | rationale |
|---|---|---|
| **cerebras** | STOCKSUNIFY2 wire-in | EQUITY T2→T1 jump; biggest single-class Sharpe boost |
| **gemini** | STOCKSUNIFY2 wire-in | Highest-leverage pipeline integration; daily commits, ready to wire |
| **deepseek** | FOREX carry+TSMOM mutate-before-kill | FOREX PF 0.28 is biggest drag on overall portfolio |
| **kilo** (late, 9.6KB) | **COMMODITY 2.0x sizing + per-symbol cap** | Highest $ PnL ROI in 0.5d; PF 4.07 track record; capital reallocation only, zero model risk |

**Verdict: 2/4 STOCKSUNIFY2, 1/4 COMMODITY, 1/4 FOREX.** Plurality = STOCKSUNIFY2.

Kilo's reordering insight: **ship the 3 trivial fast-wins (EW compound cap, LONG_TERM 3-LoC, hyro-bridge numpy) FIRST as foundation** — total ~5 LoC, ~30 minutes work — before starting any of the 2-week strategy work. They unblock observability for the bigger items.

Kilo's left-outs (high-potential, cut for budget):
- ETF emission-cap raise — STOCKSUNIFY2 delivers 1000+ EQUITY picks/day so 2-pick ETF gap is negligible
- F2/F7/F8 dashboard features — performance lifts move PFs; UI observability is secondary
- A2/A1/A6 automation — week-2 follow-ups; outage guards not performance lifts
- SEC Form 4 — incremental on top of CAN SLIM, not standalone

Kilo's highest-risk: **#4 CRYPTO drag-cohort kill** (Polymarket gate could over-block 40-60% of CRYPTO LONG volume). Mitigation: gate ONLY alpha_engine_fast + kimi_signal_tracking; HIGH_CONVICTION-tier-only elsewhere; monitor daily CRYPTO n; rollback within 48h if volume drops >50%.

## Final top-7 (cross-engine synthesis)

| # | action | doc | LoC | days | impact | risk |
|---|---|---|---|---|---|---|
| 1 | **STOCKSUNIFY2 CAN SLIM + Replicator wire-in** | A2/C1 | 80-120 | 2-3 | EQUITY PF 1.42→~1.9, n→>600, T2→T1 | mis-routing → unit-test gate |
| 2 | **FRED economic data integration** | C2 | 80-120 | 1-3 | BOND n<100→100+ + FOREX PF lift via macro context | external API drift; fallback cache |
| 3 | **COMMODITY 2.0x sizing + per-symbol cap** | A1 | 30 | 0.5 | PF 4.07/WR 67.2 already T1; safe scale | inverse-momentum blowup; per-symbol cap mitigates |
| 4 | **CRYPTO drag-cohort kill + Polymarket gate v2** | A3 | 80 | 1-2 | CRYPTO PF 1.26→~1.6; kills alpha_engine_fast PF 0.62 + kimi_signal_tracking PF 0.26 | over-aggressive kill of recovering edge; deploy w/ 7d watch |
| 5 | **LONG_TERM filter 3-LoC fix + concept_registry.py:186** | (loop1) | 3 | 0.5 | LONG_TERM filter 0→38 picks visible | none |
| 6 | **F8 Forward-vs-Backtest divergence card** | B2 | 150 | 2 | catches overfit before live bleed; would have caught alpha_engine_fast earlier | data alignment false positives; 2σ threshold |
| 7 | **F2 Per-asset-class leaderboard switcher** | B1 | 120 | 1 | operator decision-support; chips by class | minimal — pure UI |

**Total budget**: 543-623 LoC + ~9-13 days = fits 2-week ship plan.

**FREEBUFF's already-shipped FOREX P0/P1 fixes** (uncommitted in working tree) are #8 — execute commit + monitor 7d before any further FOREX work.

## Synergy pairs (3-engine consensus)

- **#1 + #6** (STOCKSUNIFY2 + F8 divergence): EQUITY new picks immediately monitored vs backtest baseline
- **#2 + #4** (FRED + Polymarket gate v2): macro-context regime filter on top of news-based gate
- **#3 + #5** (COMMODITY scale + LONG_TERM filter): concept-tagged COMMODITY positions visible on /audit

## Left out (high-potential but cut for budget)

- F4 Cohort drift heatmap (250 LoC, 3 days) — too long for 2-wk window
- Cryptopanic news/sentiment — doc C #3, defer to next sprint
- A2 Stale data-file watchdog — already partially covered by db_health.json
- F11 Per-asset-class Action Queue — UI-heavy, defer

## Highest-risk pick (consensus: F8 Forward-vs-Backtest)

Per deepseek: data alignment false positives. Mitigation: start at 2σ divergence threshold, tune after 7d. Fallback = manual weekly review.

## Recommended ship sequence

**Week 1**:
- Day 1-3: STOCKSUNIFY2 (#1) + LONG_TERM 3-LoC (#5) + COMMODITY sizing (#3)
- Day 4-5: FRED integration (#2) + commit freebuff FOREX fixes
- Day 6-7: CRYPTO drag-cohort kill (#4)

**Week 2**:
- Day 8-10: F8 divergence card (#6)
- Day 11-12: F2 leaderboard switcher (#7)
- Day 13-14: Polish + ship

## What NOT to ship (3-engine consensus rejected)

- mikestocks repo (stale >1y) — abandoned per agent C
- SCREENER_PENNYSTOCK_24H — duplicate of broken in-tree penny-skyrocket
- Cross-PC heartbeat cron — poor-ROI hostbound
- Mercury2_fast restart — intentionally disabled garbage data

## Engine notes

- **deepseek**: 5,338 bytes raw, full ranking, consistent w/ prior swarm performance
- **cerebras**: 5,777 bytes, full ranking + numeric impact estimates
- **gemini**: 3,406 bytes (terser), prose-style, partial JSON schema compliance — pulled rankings via grep
- **kilo**: TIMED OUT (>5 min on `proposals_ranking_prompt.md` 4.6KB input + 4-doc reference)

For future swarm runs on dense reference material, prefer 3-engine `consensus-3` preset. Kilo struggles on long context per recent observations.

## Inputs

- `reports/proposals_strategy_2026-05-08.md` (Agent A)
- `reports/proposals_dashboard_features_2026-05-08.md` (Agent B)
- `reports/proposals_data_integrations_2026-05-08.md` (Agent C)
- `reports/proposals_automation_2026-05-08.md` (Agent D)
- `swarm_runs/proposals_rank_20260508T200641Z/` (3 engine outputs)
- Prior loops' 16-item fix queue (`reports/loop2_3hour_summary.md`)

## Recommended user gates

User-decisions needed before any of the 7 ship:
1. Approve STOCKSUNIFY2 sibling-repo curl pull (no creds; should be safe)
2. Confirm freebuff's FOREX P0/P1 changes (currently uncommitted in working tree) — review/commit/revert
3. Confirm 2-week budget acceptable
4. Approve COMMODITY 2.0x sizing increase (live trading impact)

If user gives green, ready to start at #1. Otherwise queue.
