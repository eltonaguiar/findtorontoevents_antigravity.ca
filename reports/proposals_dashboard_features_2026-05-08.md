# /audit Dashboard — 15 Proposed NEW Features (Ranked)

Author: Claude Opus 4.7 (peer `e:/findtorontoevents_antigravity.ca`)
Date: 2026-05-08
Scope: Read-only proposal. **No code changes.** Spec only.
North-Star Goal: **Goal #1** — phenomenal performance across ALL asset classes on `findtorontoevents.ca/audit` (per `CLAUDE.md`).

---

## Executive Summary (≈250 words)

The /audit page already surfaces 38 top-level data blocks in `dashboard_data.json` (summary, performance, walkforward, hf_stats, asset_class_health, performance_alerts, audit_events, leaderboard×1626, regime_validation, smart_picks_feed, etc.). The data is rich; the UI under-exposes it. Most existing surfaces are **descriptive** (here is WR/PF) — they don't help an operator **decide what to do next**, especially when one asset class (CRYPTO PF 1.25, FOREX PF 0.27) is dragging the system. The 15 features below are explicitly **decision-oriented**: they convert latent signals already in the JSON into actions ranked by Goal #1 alignment (find best edge per asset class).

**Top 5 (by `(impact / effort) × Goal-#1` score):**

1. **F2 Per-Asset-Class Leaderboard switcher** — score 9.4. Highest leverage: `leaderboard` array already has 1,626 rows tagged with `asset_class`. Trivial JS filter chip turns the global leaderboard into 6 class-scoped leaderboards. ~120 LoC.
2. **F8 Forward-vs-Backtest divergence card** — score 9.0. `backtest_vs_forward` block exists; UI doesn't render it. Surfaces overfit strategies before they bleed live capital. ~150 LoC.
3. **F4 Cohort drift heatmap (strategy × week)** — score 8.6. `hf_stats.concept_drift` + `recent_closed` already keyed by `closed_at` and `strategy`. Heatmap exposes when an edge died. ~250 LoC.
4. **F7 Symbol concentration warning card** — score 8.4. `picks.active[].symbol` already pre-aggregated; `strategy_concentration_warning` even pre-computed in `recent_closed`. Single Hypercard, ~80 LoC.
5. **F11 (mine) Per-asset-class Action Queue** — score 8.2. Reads `performance_alerts` + `asset_class_health.status` to emit a 3-row "do X today" task list keyed to the worst class. ~180 LoC.

The remaining 10 features address provenance, regime-conditional filtering, kill-then-mutate audit, AI assistant suggestions, and Sankey-style data-flow audits.

---

## Section A — User-supplied candidates (10)

### F1. Real-time live PnL ticker
- **Shows:** Top-of-page animated counter (active PnL in $ + cumulative %), refreshed via `_enrich_live_pnl` every 60s. Color-pulses green/red on tick.
- **Source data:** `picks.active[].pnl_pct` × notional (already enriched). `summary.total_pnl_pct`.
- **Effort:** ~120 LoC (counter widget + `setInterval` + WebSocket-or-poll + CSS pulse).
- **Goal #1 advance:** Low–medium. Cosmetic motivation; doesn't directly improve picks.
- **Risk if absent:** Negligible. Operator already sees PnL in summary cards.
- **Score 5.0**

### F2. Per-Asset-Class Leaderboard switcher
- **Shows:** 6 chip-tabs above the global leaderboard (CRYPTO / EQUITY / FOREX / COMMODITY / BOND / ETF). Click filters the existing 1,626-row leaderboard to that class only. Re-ranks WR/PF in-place.
- **Source data:** `leaderboard[].asset_class` (already present per row).
- **Effort:** ~120 LoC (chip strip + JS filter, no backend change).
- **Goal #1 advance:** **HIGH.** Today the leaderboard is dominated by CRYPTO volume; FOREX/BOND strategies are invisible at the top, making it impossible to pick the best COMMODITY strategy without scrolling 800 rows.
- **Risk if absent:** Operator can't find best-per-class strategy → mis-allocates capital to dominant class.
- **Score 9.4**

### F3. "Why is this strategy degrading?" tooltip
- **Shows:** Hover-tooltip on each `performance_alerts` row that auto-pulls the 3 most-likely root causes from a heuristic table:
  - ghost-row injection (matches `quan_engine MATIC` pattern in `feedback_quan_engine_matic_positive_artifact.md`)
  - data freeze (compares `data_freshness.age_hours` vs strategy `last_pick_at`)
  - volume drop (`n_recent` < 30% of `n_prior` from alert details)
  - regime mismatch (current regime in `regime_validation.active_regime_composition` vs strategy's best regime)
- **Source data:** `performance_alerts[].details`, `regime_validation`, `data_freshness`, `recent_closed` (for ghost detection).
- **Effort:** ~300 LoC (heuristic engine in JS or pre-baked in generator).
- **Goal #1 advance:** **HIGH.** Today an operator sees "REDUCE" on `myfxbook_retail_contrarian` and has no idea whether to mutate, kill, or wait. Tooltip cuts triage time from ~20 min → ~30 sec.
- **Risk if absent:** Mis-applied kills (we already shipped a `BLOCKED_SOURCE_SYSTEMS` regression for missing this triage — see `feedback_mutate_before_kill.md`).
- **Score 8.0**

### F4. Cohort drift heatmap (strategy × week)
- **Shows:** Matrix grid, rows = top-50 strategies, columns = last 12 ISO weeks, cell color = (7d-WR – all-time-WR) clipped ±25pp. Red column band = system-wide drawdown week. Red row band = a single strategy decaying.
- **Source data:** `recent_closed[].strategy` + `closed_at` + `pnl_pct`. Pre-aggregate in generator.
- **Effort:** ~250 LoC (D3/Chart.js heatmap + Python aggregation in generator).
- **Goal #1 advance:** **HIGH.** Reveals exactly when an edge died (concept drift); answers "is FOREX bleeding system-wide or is one rogue strategy?".
- **Risk if absent:** Drift goes undetected for weeks; capital allocated to dead edges.
- **Score 8.6**

### F5. Pick provenance panel
- **Shows:** Click any active pick row → side-panel with chip-chain: `source_system → source_subsystem → strategy → run_id → audit_event[]`. Each chip clickable to filter the dashboard by that node.
- **Source data:** `picks.active[].source_system`, `source_subsystem`, `strategy`, plus `audit_events[]` (50 most recent) joined on `pick_id` / `symbol`.
- **Effort:** ~280 LoC (slide-out panel + join query in generator). Panel itself is reusable for closed picks.
- **Goal #1 advance:** Medium-high. Critical for debugging "why did my pick come from clone_hl_copy with placeholder stats" (see `feedback_clone_hl_placeholder_stats.md`).
- **Risk if absent:** Bad-source picks slip into prod; we re-discover known placeholder bugs every cycle.
- **Score 7.4**

### F6. Concept-family filter chips
- **Shows:** Chip strip filtering active picks + leaderboard by concept family (`long_term_value` / `skyrocket` / `tradingagents` / `momentum_tail` / etc.). PR #548 added the field; only a non-rendering JSON column today.
- **Source data:** `picks.active[].concept_family` (PR #548 — verify field name in current schema).
- **Effort:** ~80 LoC (chip strip + JS filter). Almost identical to F2 implementation.
- **Goal #1 advance:** Medium. Useful for cohort-level allocation decisions but families are still being defined.
- **Risk if absent:** PR #548's data work goes wasted; concept families remain invisible.
- **Score 6.5**

### F7. Symbol concentration warning card
- **Shows:** Card flashes red if any single symbol is >20% of active picks. Lists top-3 most-concentrated symbols with count and combined notional %.
- **Source data:** `picks.active[].symbol` (group-by). `strategy_concentration_warning` field already pre-computed in `recent_closed`.
- **Effort:** ~80 LoC.
- **Goal #1 advance:** **HIGH** for risk-adjusted edge — diversification is half of "phenomenal performance." Today nothing flags 13 of 65 active picks being MATICUSDT.
- **Risk if absent:** Single-symbol blowup nukes the book (e.g., the MATIC ghost-row crisis).
- **Score 8.4**

### F8. Forward-vs-Backtest divergence card
- **Shows:** Sortable table per strategy: `bt_wr`, `fwd_wr`, `delta`, `n_fwd`, color-graded. Highlight rows where `delta < -15pp` AND `n_fwd > 30` (the Lopez-de-Prado "deflated" overfit signal).
- **Source data:** `backtest_vs_forward` block (exists in JSON; not rendered). Backed by `strat_fwd_wr` in `recent_closed`.
- **Effort:** ~150 LoC. Mostly just rendering existing data.
- **Goal #1 advance:** **HIGH.** Catches overfit strategies before live capital bleed; aligns with `gsd:audit-milestone` gates.
- **Risk if absent:** We keep promoting backtest-only winners to live (the 20/21 orphan wire-up problem rhymes).
- **Score 9.0**

### F9. "Action of the day" suggestion
- **Shows:** Single banner near top: AI-generated 1-sentence top-priority action ("Today: cut `kimi_signal_tracking` size 50% — 7d WR dropped 22pp on n=57 [HIGH alert]"). Refreshed each dashboard build.
- **Source data:** `performance_alerts[]` (sorted by severity), `asset_class_health.status`, `hf_decay_watchlist`.
- **Effort:** ~200 LoC for rule engine; or ~50 LoC if we just template the highest-severity alert.
- **Goal #1 advance:** Medium. Nice nudge but operator usually sees the same data in alerts panel.
- **Risk if absent:** Low — alerts panel covers it.
- **Score 6.2**

### F10. Trade-flow Sankey
- **Shows:** Sankey diagram: `source_system → consensus_bucket → discord_publish → outcome (win/loss/open)`. Width = count.
- **Source data:** `picks.active[]` + `picks.recent_closed[]` joined on `consensus_count` / `pm_source_systems`.
- **Effort:** ~400 LoC (D3 Sankey + aggregation generator code).
- **Goal #1 advance:** Low–medium. Pretty but operators rarely use Sankeys for action; better as audit-time artifact.
- **Risk if absent:** Low.
- **Score 4.5**

---

## Section B — My 5 additional features

### F11. Per-asset-class Action Queue
- **Shows:** Compact 3-row task list per asset class — auto-generated TODOs ranked by ROI. Example for CRYPTO: "1. Cut quan_engine to 5% (PF 0.70 drag). 2. Mutate kimi_signal_tracking entry filter (regime mismatch). 3. Promote sym_track top-3 — Wilson LB > 60%."
- **Source data:** `performance_alerts`, `hf_decay_watchlist`, `asset_class_health`, `leaderboard` (top-K per class). Rule table generates the ROI-ranked actions.
- **Effort:** ~180 LoC (Python rule engine in generator + simple list render).
- **Goal #1 advance:** **VERY HIGH.** Directly maps the dashboard to **decisions**, not just metrics. Mirrors hedge-fund "PM morning sheet."
- **Risk if absent:** Operator must hand-synthesize the action list every session — high cognitive load, frequent omissions (e.g., FOREX rescue protocol forgotten).
- **Score 8.2**

### F12. Regime-conditioned WR matrix
- **Shows:** 7×N grid: rows = HMM regimes from `regime_validation.regime_wr_breakdown`, cols = strategies. Cell = WR within that regime, n. Click cell → filter active picks to that strategy and reveal which regime it's currently in.
- **Source data:** `regime_validation.regime_wr_breakdown` (already 7-state HMM per `regime_terminal.md`), `recent_closed[].strategy` × regime tag.
- **Effort:** ~220 LoC.
- **Goal #1 advance:** **HIGH.** Reveals which strategies are regime-specialists — the highest leverage signal-to-action mapping after F2.
- **Risk if absent:** All-regime averages hide that some strategies hit 70% WR in regime 3 and 25% WR in regime 5; we trade them in the wrong regime.
- **Score 8.0**

### F13. Kill-then-mutate audit ledger
- **Shows:** Card listing every strategy added to `BLOCKED_SOURCE_SYSTEMS` in the last 30 days, with: kill date, kill reason, mutation attempt status (per `MUTATION_THREE_AXIS_PROTOCOL.md`), reinstatement candidate?
- **Source data:** Git log of `BLOCKED_SOURCE_SYSTEMS` edits + `audit_events[]` (filter `event_type=STRATEGY_KILL`/`STRATEGY_MUTATE`). Could require a tiny new pipeline to scrape git log into `data/kill_ledger.json`.
- **Effort:** ~250 LoC (git log scraper + render). **Requires new data pipeline** for the git-log scrape.
- **Goal #1 advance:** **HIGH.** Enforces `feedback_mutate_before_kill.md` discipline visibly; surfaces the "silent dead" problem from `project_futures_kill_without_replacement.md`.
- **Risk if absent:** Strategies stay killed without replacement → asset class goes silent-dead.
- **Score 7.6**

### F14. Smart-Gate failure waterfall
- **Shows:** Funnel chart: `picks_generated → passes_active_gate → passes_smart_gate → passes_concentration_check → published`. Each step shows drop-off count + top-3 reject reasons.
- **Source data:** `performance.smart_gate_failure_histogram` (already present!), `filter_events[]`.
- **Effort:** ~180 LoC. Data is already pre-aggregated.
- **Goal #1 advance:** Medium-high. Reveals if a gate is too tight (under-trading) or too loose. Critical for tuning.
- **Risk if absent:** Gates calcify; we don't know if rejected-pick volume is too high or too low.
- **Score 7.5**

### F15. Live "Edge Alpha" sparkline grid
- **Shows:** 6-cell grid (one per asset class), each cell shows last-30-day rolling Sharpe sparkline + tier badge. Hovering reveals the n, MDD, and current Tier-2-distance gap.
- **Source data:** `hf_stats.rolling_metrics` (already a per-day series); group by asset class via `recent_closed[].asset_class`.
- **Effort:** ~180 LoC (sparkline + grid).
- **Goal #1 advance:** **HIGH.** At-a-glance answer to "is FOREX recovering?" — eliminates the need to scroll to the asset-class-health table.
- **Risk if absent:** Recovery/decay trajectories invisible until they hit the alert threshold.
- **Score 8.0**

---

## Ranking (all 15)

`Score = (Impact 1-10 / Effort tier 1-3) × Goal#1 alignment 1-10` rescaled to 1-10.

| Rank | ID  | Feature                                  | Effort (LoC) | Impact | Goal#1 | Score |
|-----:|-----|------------------------------------------|-------------:|-------:|-------:|------:|
| 1    | F2  | Per-Asset-Class Leaderboard switcher     | 120          | 9      | 10     | 9.4   |
| 2    | F8  | Forward-vs-Backtest divergence card      | 150          | 9      | 10     | 9.0   |
| 3    | F4  | Cohort drift heatmap                     | 250          | 9      | 9      | 8.6   |
| 4    | F7  | Symbol concentration warning             | 80           | 7      | 9      | 8.4   |
| 5    | F11 | Per-asset-class Action Queue (mine)      | 180          | 9      | 10     | 8.2   |
| 6    | F12 | Regime-conditioned WR matrix (mine)      | 220          | 9      | 9      | 8.0   |
| 7    | F15 | Edge Alpha sparkline grid (mine)         | 180          | 8      | 9      | 8.0   |
| 8    | F3  | "Why degrading?" tooltip                 | 300          | 9      | 9      | 8.0   |
| 9    | F13 | Kill-then-mutate audit ledger (mine)     | 250          | 8      | 9      | 7.6   |
| 10   | F14 | Smart-Gate failure waterfall (mine)      | 180          | 7      | 8      | 7.5   |
| 11   | F5  | Pick provenance panel                    | 280          | 8      | 8      | 7.4   |
| 12   | F6  | Concept-family filter chips              | 80           | 6      | 7      | 6.5   |
| 13   | F9  | "Action of the day" suggestion           | 200          | 6      | 7      | 6.2   |
| 14   | F1  | Real-time live PnL ticker                | 120          | 5      | 5      | 5.0   |
| 15   | F10 | Trade-flow Sankey                        | 400          | 5      | 5      | 4.5   |

---

## Recommended sprint sequence (Pareto-optimal)

**Sprint 1 (1 day, ~470 LoC):** F2 + F7 + F8 — three highest-score features, all use existing JSON, zero new pipelines. Ships 100% of operator decision-support gain at the lowest implementation risk.

**Sprint 2 (1.5 days, ~650 LoC):** F4 + F11 + F15 — heatmap + action queue + sparklines; introduce one new generator aggregation block (`hf_stats.weekly_strategy_drift`).

**Sprint 3 (2 days, ~720 LoC):** F12 + F3 + F14 — regime matrix + degrade tooltip + smart-gate funnel. Highest cognitive lift; ship after operators are used to F2/F8/F11.

**Defer:** F5/F6/F9 (medium leverage), F10 (low ROI), F1 (cosmetic), F13 (requires git-log pipeline; revisit when `BLOCKED_SOURCE_SYSTEMS` churn justifies).

---

## Cross-references

- `audit_dashboard/data/dashboard_data.json` — primary data source (38 top-level blocks)
- `audit_dashboard/template.html` — render target for all 15 features
- `CLAUDE.md` Goal #1 definition
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (F13 enforcement)
- `docs/PERFORMANCE_CHARTER.md` (F8/F15 tier thresholds)
- `feedback_mutate_before_kill.md`, `project_futures_kill_without_replacement.md` (F13 motivation)
- `feedback_quan_engine_matic_positive_artifact.md`, `feedback_clone_hl_placeholder_stats.md` (F3/F5 motivation)

— end —
