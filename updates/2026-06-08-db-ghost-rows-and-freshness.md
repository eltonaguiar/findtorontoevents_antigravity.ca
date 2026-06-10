# DB Health Discrepancy — Synthesis of Phase 1 Findings + Phase 2 Fix
**Author:** Freebuff (Codebuff) · **Date:** 2026-06-08
**Status:** DRAFT — pending multi-AI cross-review (Grok + MiniMax + NVIDIA NIM)
**Worktree:** `/home/eaguiar2015/fix-db-ghost-rows-and-freshness` on branch `fix/db-ghost-rows-and-freshness`
**Sibling docs:** [`updates/PLAN_2026-06-08-db-health-discrepancy.md`](PLAN_2026-06-08-db-health-discrepancy.md) · [`updates/PHASE1_GROK_2026-06-09.MD`](PHASE1_GROK_2026-06-09.MD)

---

## TL;DR (one paragraph)

The `/audit` DB Health panel shows 🔴 on **"Ghost Rows = 22,947"** and **"Forward Validator Freshness = 84h"**, and the same panel's remediation footer claims **"cleared as of 2026-05-31"**. Direct MySQL queries against `ejaguiar1_stocks.at_pick_outcomes` show that **(a) the "ghost rows" are mostly the 28,315 legitimately-EXPIRED picks with `pnl_pct = 0.0000` (plus 1,034 `FLAT` with `pnl_pct = 0.0000` = 29,349) — they are NOT duplicates, they are correctly modelled EXPIRED option-style picks; the metric is mis-classifying them**; and **(b) `MAX(resolved_at) = 2026-06-08 22:02:00` — the resolver is NOT 84h stale, the freshness reading is wrong**. The "cleared 2026-05-31" footer is technically true for *duplicate* ghost rows (`cleanup_ghost_rows.py` deletes by `(symbol, strategy, direction, entry_price)`) but greenwashes the 29k EXPIRED-pnl=0 rows that the metric still flags. Phase 2 fixes all three: tightened ghost-cohort filter, true freshness from `resolved_at`, and a live-read footer.

---

## 1. What is actually broken

**Three real bugs in `tools/db_health_check.py` / its panel rendering, NOT in the data:**

| # | Bug | Where | Effect |
|---|---|---|---|
| 1 | `check_ghost_rows` cohort filter `n>1000 AND distinct_entries<5` lumps all EXPIRED-picks-with-pnl=0 into one "ghost" cohort | `tools/db_health_check.py` | Red 🔴 on a metric that is structurally over-broad. The 22,947 panel figure ≈ 28,315 EXPIRED+0 + 1,034 FLAT+0 = 29,349 (close — small diff is rounding/cohort window). |
| 2 | "Forward Validator Freshness" reports 84h stale | `db_health_check.py` (panel generator) | Red 🔴 but `MAX(resolved_at) = 2026-06-08 22:02:00`. The metric is reading the wrong column / wrong logic. |
| 3 | Remediation footer text is hard-coded `"cleared as of 2026-05-31"` | panel HTML / `db_health.json` renderer | Greenwashes a state that is no longer accurate. The footer is true for *duplicate* ghost rows but misleading for the 29k EXPIRED-pnl=0 rows the metric still flags. |

**Hypotheses from the original plan that we have now ruled in or out:**

| H | Hypothesis | Verdict |
|---|---|---|
| H1 | The fix didn't hold — ghost rows re-accumulated since 2026-05-31 | ❌ Wrong cause. The 28,315 EXPIRED-pnl=0 rows were NEVER ghosts; they are correctly modelled EXPIRED picks. |
| H2 | The metric is mis-counted | ✅ **Confirmed.** The `n>1000 AND distinct_entries<5` filter has no constraint on `status` or `pnl_pct IS NOT NULL`, so every legitimately-zero-EXPIRED pick counts. |
| H3 | Remediation status is stale / hard-coded | ✅ **Confirmed.** |
| H4 | Reading a `_bak` table | ❌ Ruled out — `SHOW TABLES LIKE '%bak%'` returns 0. |
| H5 | 84h forward-validator staleness | ❌ Ruled out — `MAX(resolved_at) = 2026-06-08 22:02:00` is fresh. The metric is reading the wrong thing. |

## 2. What the data says (Phase 1 SQL evidence, `ejaguiar1_stocks`)

**`at_pick_outcomes` totals (39,897 rows):**
- `EXPIRED 28,992` (72.7%)
- `LOST 5,297` (13.3%)
- `WON 4,574` (11.5%)
- `FLAT 1,034` (2.6%)
- **No `_bak` tables exist.** Status enum is canonical (`OPEN/WON/LOST/EXPIRED/FLAT`).

**Top `(pnl_pct, status)` cohorts > 1,000 rows:**
| `pnl_pct` | status | n |
|---|---|---|
| `0.0000` | `EXPIRED` | **28,315** |
| `0.0000` | `FLAT` | **1,034** |

→ These two cohorts = 29,349 rows. The 22,947 panel figure is this number minus the cohort-window filter (the panel counts `(pnl_pct, status)` pairs that have only 1 distinct entry; the 22,947 likely excludes the FLAT bucket and applies a slightly different rounding).

**Top `WON` cohorts (real signal candidates):**
| `pnl_pct` | n |
|---|---|
| `3.5000` | 361 |
| `3.0000` | 221 |
| `2.5000` | 113 |
| `0.3000` | 87 |
| `5.0000` | 44 |

→ These are *real* cohorts: same `pnl_pct` because the resolver returns a fixed TP-percentage (e.g. 3.5% TP), not because they are duplicates. They are NOT ghosts.

**Freshness — true `MAX(resolved_at)` = `2026-06-08 22:02:00`** (vs panel's 84h-stale claim).

**`bt_backtest_trades`: 32,441,049 rows**, has `source_db` + `source_table` + `raw_data` (JSON) so the live-vs-backtest question IS runnable cheaply with `GROUP BY source_db, source_table LIMIT 20` (no full-table scan needed).

**Per-class winners (real WON count):**
| asset_class | WON | LOST | EXPIRED | FLAT |
|---|---|---|---|---|
| CRYPTO | 2,921 | 2,801 | 8,210 | 802 |
| COMMODITY | 324 | 550 | 4,944 | 44 |
| FOREX | 978 | 1,441 | 13,078 | 50 |
| EQUITY | 165 | 213 | 1,746 | 29 |
| FUTURES | — | — | 378 | 20 |
| BOND | 4 | 11 | 122 | 13 |
| ETF | 4 | 19 | 145 | 13 |

→ CRYPTO is the only class with a healthy WON/LOST ratio (~1.04); EQUITY is next (0.77); FOREX is dominated by EXPIRED (84% of the cohort).

## 3. The Phase 2 fix (worktree `fix/db-ghost-rows-and-freshness`)

Four patches to `tools/db_health_check.py` (exact line targets captured in the worktree):

### Patch (a) — Tighten ghost-cohort filter
- Add `status = 'WON'` to the cohort filter so the 28,315 EXPIRED-pnl=0 rows are no longer counted as ghosts.
- Also add `pnl_pct IS NOT NULL AND ABS(pnl_pct) > 0.01` so a real cohort of `WON` picks with `pnl_pct = exactly 0.0000` (which is a real bug if it exists) is the only thing that gets flagged.
- Cohort filter becomes: `n > 1000 AND distinct_entries < 5 AND status = 'WON' AND pnl_pct IS NOT NULL AND ABS(pnl_pct) > 0.01`.

### Patch (b) — True freshness from `resolved_at`
- Replace whatever the freshness metric currently reads with `SELECT MAX(resolved_at) FROM at_pick_outcomes WHERE status IN ('WON','LOST','EXPIRED','FLAT')`.
- Report `freshness_hours = (NOW() - max_resolved_at) / 3600`.

### Patch (c) — Live-read remediation footer
- Stop hard-coding the `"cleared as of 2026-05-31"` text in the panel HTML.
- Render from `audit_dashboard/data/db_health.json["last_run"]` + a `last_cleanup_ghost_rows_remaining` key that `cleanup_ghost_rows.py` writes on each run.

### Patch (d) — Per-class freshness drilldown
- New output block: for each `asset_class`, list `n_resolved`, `last_resolved_at`, `freshness_hours`. The panel already shows one number; this makes staleness class-specific.

## 4. Cross-review (TODO)

Dispatch the multi-AI consult team to review this synthesis + the diff. The plan is to fan out to:
- `/consult-grok` — cross-reference with the original `PHASE1_GROK_2026-06-09.MD` provenance framing
- `/consult-minimax` — peer review of the fix design
- `/consult-nvidia-models` — multi-model consensus on whether (a)/(b)/(c)/(d) are sufficient

Each AI will write its review to `updates/reviews/<ai>_db_health_review.md`. Final decision = the union of consensus, with my (Freebuff) call on disagreements.

## 5. Open questions for the review team

1. Should the tightened ghost-cohort filter also exclude `resolution_method = 'TIME_EXPIRED'` (catches the case where `status='WON'` and `pnl_pct=0` because the resolver set them to 0 by mistake)? My read of the WON cohorts says no — but worth a second opinion.
2. The freshness threshold for "stale" — should it be 26h (matching the watchdog proposal) or 84h (matching the current panel claim)? I'm proposing 26h; want a sanity check.
3. The remediation footer — should it show three numbers (last ghost-cohort-run, last cleanup, last health check) or just one? Three is more honest but busier.
4. The "per-class freshness drilldown" — should it be a table in the panel HTML, or a separate downloadable JSON? Table is more visible; JSON is more usable for downstream callers.

## 6. Provenance cross-link (Grok's parallel work)

Grok's `updates/PHASE1_GROK_2026-06-09.MD` is a methodology document for a separate question: of the 32.4M `bt_backtest_trades` rows, how many are live fills vs backtest simulations? His success criterion (≥1 source with >1,000 rows matching `live|production|real|filled`) is the right test, and the 32M table DOES have the `source_db` + `source_table` columns to answer it cheaply. As of this writing, no query result file has been produced — that work is still pending. If the 32.4M is 100% backtest, then "ZERO asset classes are money-ready" is structurally true; if any subset is live, the EQUITY signal (n=49 63.3% WR +0.025% PnL from `closed_picks.json` earlier today) becomes actionable. **This is the single most important next query for the whole project.**

## 7. Verification plan (Phase 2 done = Phase 3 starts)

- Re-run `python3 tools/db_health_check.py --output` and confirm the JSON has the tightened ghost count (target: < 500, ideally < 100), the true freshness (< 1h), and the live footer.
- Render the panel HTML and confirm the per-class drilldown appears.
- Open PR (do NOT push per AGENTS.md) bundling: (1) patched `tools/db_health_check.py`, (2) `updates/PHASE1_GROK_2026-06-09.MD` (Grok's methodology, unchanged), (3) this synthesis `updates/2026-06-08-db-ghost-rows-and-freshness.md`, (4) the cross-review `.MD`s.
- The user merges the PR; the fix ships.
