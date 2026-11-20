# Phase D — Backtest DB Diagnosis (D1 / D2 / D3)

**Date:** 2026-11-20 · **Seat:** SUBQ- / subq-savant-1.4 · **Scope:** diagnosis only — nothing repaired, no commits, no workflow edits.

---

## D1 — Does the import job exist? → **BROKEN, not retired, not never-automated**

Two importer artifacts exist in the tree and **neither runs on a schedule**:

| Artifact | State | Evidence |
|---|---|---|
| [`audit_trail/import_backtest_trades.py`](audit_trail/import_backtest_trades.py) | Manual CLI only. Writes both tables (`INSERT INTO bt_backtest_runs`, `TRUNCATE TABLE bt_backtest_runs`). | Present in main tree (30,721 bytes). Grep hits for `bt_backtest_runs` at the script's insert/summary sites. |
| [`tools/migrate_backtests_to_backtests_db.py`](tools/migrate_backtests_to_backtests_db.py) | Manual one-shot cross-DB copier. | Docstring usage: `python tools/migrate_backtests_to_backtests_db.py --tables bt_backtest_trades bt_backtest_runs` — a CLI invocation, not a workflow step. |
| [`.github/workflows/bt-backtest-trades-sync.yml`](.github/workflows/bt-backtest-trades-sync.yml) | **Has a cron (`24 4 * * 0`) but is a DRAFT** — header line 1: `# DRAFT WORKFLOW — DO NOT ENABLE WITHOUT OPERATOR REVIEW`. Its own header says to enable it you must `git mv` the `.draft` file over the `.yml`. | Read in full. |
| `.github/workflows/bt-backtest-trades-sync.yml.draft` | The original, also draft-marked, `workflow_dispatch` + `cron: "0 4 * * 0"`. | `diff` against the `.yml` shows only host/secret/step wording differences. |

**Why "broken" and not "retired" or "never automated":**
- Not *never automated* — the sync workflow was written with a cron and the tables were populated in bulk.
- Not *retired* — nothing reads as an intentional decommission; the workflow is explicitly gated as "DRAFT — DO NOT ENABLE", i.e. pending, and the importer scripts are still referenced by health/freshness tooling.
- *Broken* — the data stopped: `bt_backtest_runs` is frozen at **2026-03-06 23:58:10**, while the trades table kept receiving rows until **2026-05-13**, then also froze. The scheduled job that should refresh them is the un-enabled draft.

**Git history:** `git log --oneline -- audit_trail/import_backtest_trades.py tools/migrate_backtests_to_backtests_db.py .github/workflows/bt-backtest-trades-sync.yml*` returns a single commit — `7ab67511177 Merge pull request #977 from eltonaguiar/feat/kilo-todo-sweep-final`. `git log -S 'bt_backtest_runs' --oneline -15` returns the same merge plus aggregation/doc commits (`80c116ae361 Cross-system aggregation 2026-11-20 01:02 UTC [skip ci]`, `56f43c6a2ce feat(audit3): register the backtest evidence the tribunal could not see`). No commit in history removes or disables a previously-active importer — the automation was never turned on.

---

## D2 — Divergence, **measured** (not the brief's numbers)

Both databases were reachable from this host on this run (the earlier `Access denied ... 142.181.219.3` was **not** reproduced). Read-only queries only; password never printed.

| Measurement | `ejaguiar1_backtests` | `ejaguiar1_stocks` |
|---|---|---|
| `bt_backtest_trades` rows (`COUNT(*)`) | **32,676,918** | **32,441,049** |
| `bt_backtest_runs` rows | **285** | **285** |
| `bt_backtest_trades` newest row (PK-ordered tail) | id **32,724,171**, `imported_at` **2026-05-13 00:03:45** | — |
| `bt_backtest_trades` oldest row | id 1, `imported_at` **2026-03-06 23:57:57** | — |
| `bt_backtest_runs` `imported_at` min/max | **2026-03-06 23:58:10** (single value — every run row frozen) | — |

**Corrections to the brief:**
- The brief's **34,619,493** vs **27,212,129** (~7.4M divergence) does **not** match measurement. Measured divergence is **235,869 rows** (32,676,918 − 32,441,049), i.e. backtests-side holds slightly *more*. The brief's figures are stale or from a different table/snapshot — treat them as superseded.
- The brief's staleness claim for `bt_backtest_runs` (**2026-03-06**) is **confirmed exactly**: max `imported_at` = 2026-03-06 23:58:10.
- Note the `COUNT(*)` on trades and the PK tail disagree slightly (32,676,918 counted vs max id 32,724,171) — expected with deleted/ghost rows; the max-id is not a row count.

**Staleness vs thresholds** ([`tools/db_freshness_check.py`](tools/db_freshness_check.py): "backtests: GREEN < 48h, YELLOW 48-168h, RED > 168h"): 2026-03-06 → 2026-11-20 is **259 days ≈ 6,216 h**, i.e. **RED**, roughly 37× past the 168h ceiling.

---

## D3 — Downstream cost, and fix-vs-retire

### `bt_backtest_trades` — consumers
- [`tools/edge_extractor.py`](tools/edge_extractor.py) — `SELECT asset_class, strategy, pnl_pct, ... FROM bt_backtest_trades`; feeds edge extraction (offline analysis output).
- [`tools/db_freshness_check.py`](tools/db_freshness_check.py) — freshness gate; writes `audit_dashboard/data/db_freshness.json`, which surfaces on the audit dashboard. **This is the one live-surface consumer.**
- [`tools/db_health_check.py`](tools/db_health_check.py) — counts, OPEN status, indexes; operational health output.
- [`tools/cross_db_consistency.py`](tools/cross_db_consistency.py) — per-strategy trade counts for cross-DB comparison.
- [`tools/wave0_fast_queries.py`](tools/wave0_fast_queries.py), [`tools/wave0_census.py`](tools/wave0_census.py), [`tools/cleanup_ghost_rows.py`](tools/cleanup_ghost_rows.py), [`tools/test_ghost_cleanup.py`](tools/test_ghost_cleanup.py) — diagnostics / one-off cleanup.
- [`tools/sql_edge_analyzer.py`](tools/sql_edge_analyzer.py) — explicitly does **not** use it ("Focuses on at_raw_picks ... NOT bt_backtest_trades").

### `bt_backtest_runs` — consumers
- [`audit_trail/dashboard_generator.py`](audit_trail/dashboard_generator.py:11354) — **confirmed**, but with a correction: it reads `bt_backtest_runs` from the **local SQLite `data/audit_trail.db`** via `_safe_sqlite`, not from `ejaguiar1_backtests` MySQL. It selects `strategy, total_trades, wins, losses, win_rate, total_return, sharpe FROM bt_backtest_runs WHERE total_trades >= 5` to build the strategy table's backtest win-rate and decay columns on **/audit**. So the MySQL copy being frozen does not directly starve /audit — the SQLite copy does, and it is similarly stale if it was populated from the same frozen source.
- [`tools/_gen_db_schema_doc.py`](tools/_gen_db_schema_doc.py) — schema doc generation only.
- [`incubator/backtest_team/batch_backtest_all.py`](incubator/backtest_team/batch_backtest_all.py:251) — writes backtest results into the runs table.

### Verdicts
- **`bt_backtest_runs` → FIX.** It is small (285 rows), it has real consumers (the /audit strategy table via SQLite, the schema doc), and its schema is meaningful aggregated PF/Sharpe per strategy. Refreshing it is cheap; retiring it would silently null out /audit's backtest win-rate/decay columns. Frozen since 2026-03-06 means every "bt_wr" shown there is 8 months old.
- **`bt_backtest_trades` → FIX the sync, don't retire.** 32.7M rows of real entry+exit+TP+SL is the highest-value backtest evidence in the estate, and at least one tool (`db_freshness_check`) reads it on a live surface. Retiring it would discard irreplaceable evidence. The divergence (235,869 rows) is small enough that a single incremental sync closes it — the draft workflow already implements exactly that (PK-windowed, `INSERT IGNORE`, resumable).

**Recommended fix (NOT applied — diagnosis only):** enable the existing draft by `git mv .github/workflows/bt-backtest-trades-sync.yml.draft .github/workflows/bt-backtest-trades-sync.yml` after operator review, run `tools/migrate_backtests_to_backtests_db.py --dry-run` locally first, and confirm `DB_PASS_STOCKS` / `DB_PASS_BACKTESTS` secrets exist. For `bt_backtest_runs`, run `audit_trail/import_backtest_trades.py` (or the migrate tool with `--tables bt_backtest_runs`) once to refresh the 285 aggregated rows.

---

## Ownership

**Unattributable from the repo as it stands.** No `CODEOWNERS` file exists in the tree (`find . -maxdepth 3 -name CODEOWNERS` → empty). The only git authorship on the importer/sync files is the merge commit `7ab67511177 ... eltonaguiar 2026-11-19 Merge pull request #977`, which is a merge, not an original author. The workflow's own header assigns the decision to the "operator". Best available answer: **operator (eltonaguiar) owns the enable/disable decision**; no individual engineer is attributable as maintainer.

---

## What I could not determine

- Which process originally wrote the trades table up to 2026-05-13 — no workflow in the repo does it, so it was likely a manual/local run, but I have no log proving which.
- Whether the SQLite `data/audit_trail.db` `bt_backtest_runs` is as stale as the MySQL copy — I read the generating code, not the SQLite file's contents.
- The source of the brief's 34.6M / 27.2M figures — they do not match any measurement I made and I could not reproduce them.
- `MAX(imported_at)` on the full trades table times out (a full scan over 32.7M rows exceeds the 90s read timeout); I used the PK-ordered tail instead, which is exact for the newest row but not a global max.

---

### Verification
- Every file claim cites a path (and line where known), read from the tree.
- Every DB number came from a query whose output I saw in this session.
- No repair, no writes, no commits, no workflow edits were made — the only file created is this report.
- No credentials appear in this document.
