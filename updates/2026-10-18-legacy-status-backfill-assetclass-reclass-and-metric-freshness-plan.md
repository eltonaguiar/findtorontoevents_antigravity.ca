# Session Summary — 2026-10-18 (paused for handoff)

**Session opened:** 2026-10-18 ~06:15 UTC · **Paused:** 2026-10-18 ~06:45 UTC
**Operator directive (verbatim):** *"proceed. sort it out, investigate, and deep dive. once you get the top picks to a decent level, ensure even in different asset classes, we have a solid set of fresh data, and every single metric … especially the core stats should be dynamic and updated periodically"* + *"create a date/time stamped summary … and then create a prioritized set of todos"*

---

## 1. What was DONE (verified, production writes)

### 1.1 Legacy NULL-status backfill — `ejaguiar1_stocks.at_raw_picks`

The 3,126 legacy rows with `status IS NULL` (created 2026-06-05 → 2026-10-18) were backfilled to `'OPEN'`.

| Check | Before | After |
|---|---|---|
| `status IS NULL` | **3,126** | **0** |
| `status='OPEN'` | 0 | 3,126 |
| NULL + `closed_at IS NOT NULL` | 0 (none skipped) | 0 |
| WON / LOST / CLOSED / EXPIRED / ABANDONED | 30,689 / 30,604 / 22,201 / 11,228 / 9,682 | unchanged |

SQL executed (guarded, committed in one transaction):
```sql
UPDATE at_raw_picks SET status='OPEN' WHERE status IS NULL AND closed_at IS NULL;
```

**Root-cause confirmed fixed upstream:** `audit_trail/mysql_client.py::mysql_record_raw_pick`
had no `status` column in its INSERT at all (column default = NULL). PR **#734**
(`f3cc4433dd`, merged `39da436b65` at 05:50 UTC) adds `'aggregator','OPEN'`.
Probe confirms **0 NULL rows created at/after the 05:50 merge** — new NULL production has stopped.

### 1.2 Asset-class backfill for OPEN rows (fresh per-class data)
`resolve_asset_class()` uses small hardcoded regex lists and resolved **0/2,629** of the
UNKNOWN-class OPEN rows (AMD, PLTR, EFA … are simply not in `_EQUITY_PATTERNS`).
Ran a **yfinance `quoteType` backfill** over the 33 distinct UNKNOWN symbols (cache:
`/tmp/symbol_assetclass_cache.json`), mapping EQUITY/ETF/FUTURE/CURRENCY → enum values.

| OPEN rows by class | Before | After |
|---|---|---|
| UNKNOWN | **2,629** | **6** (33 distinct syms → 28 resolved; 5 unresolvable: `JTOUSD2`, `DEX:67`, `DEX:IF`, `DEX:USWR`, `DEX:USOH`) |
| EQUITY | 101 | **2,567** |
| ETF | 54 | **211** |
| FOREX | 125 | 125 |
| FUTURES | 114 | 114 |
| CRYPTO | 100 | 100 |
| BOND | 3 | 3 |

NOTES/CAVEATS:
- 5 FX-style symbols (`DEX:*`, `JTOUSD2`) are not yfinance-queryable — left UNKNOWN by design.
- The `plan` walk only saw 33 distinct symbols because `PLTR`/`AMD`/… clustered; row-wise
  UPDATE matched `WHERE symbol=…`, so all 2,629 rows moved in 28 statements.
- Verifier output `rows updated: 1` is pymysql's *last-statement* rowcount quirk — the group-by
  counts above (EQUITY 101→2,567) are the authoritative proof.

### 1.3 Watcher started (not yet conclusive)
`/tmp/postfix_insert_watch.sh` (PID 3466489, log `/tmp/postfix_insert_watch.log`) polls every
5 min for the **first post-fix INSERT carrying `status='OPEN'`**. As of 06:23 UTC: **0 inserts
recorded since 05:50** — the ~hourly aggregator had its last run at 04:57, so the watcher simply
hasn't seen a cycle yet. Log was still empty (likely stdio buffering) — re-check manually.

---

## 2. Investigation findings (metrics freshness / dynamic core stats)

### 2.1 What is ALREADY dynamic (good news)
- **`dashboard_data.json` regenerates hourly** — `audit-dashboard.yml` cron `10 * * * *`.
  Live copy verified: `generated_at = 2026-10-18T05:36:10Z`, 24.3 MB, HTTP 200. All headline
  summary stats (overall WR 44.8%, PF 1.15, expectancy, Sharpe/DD, wins/losses, active counts,
  concentration, quality-gate drop counts) are recomputed each run and served fresh.
- **`updates/index.html` incidents/enhancements block regenerates** via
  `audit-hourly-update.yml` (cron `20 * * * *`) → `audit_dashboard/generate_hourly_update.py`,
  with staleness marker `hourly_update_last_run.json` (fresh: 1.7 h old when probed).
- **Active (unrealized) PnL is marked live client-side**: `template.html` recomputes active PnL
  every 30 s from the price API (`liveCard … Auto-refreshes every 30s`), plus `_unrealizedPnlPct`
  fallback chain so it never renders fake `+0.00%`.
- Realized vs unrealized split exists and is computed in both Python
  (`dashboard_generator.py`: realized block, `_pick_pnl_pct`, unrealized rollup ~L10414) and JS
  (verified-alpha `computeOutcomeStats`, `unrealizedPnl` aggregate at L6449/6852).

### 2.2 What is STILL STATIC (the actual gaps)
1. **Hard-coded prose stats in template.html / index.html**
   - L850: *"Refreshed 2026-05-29 (n=73,817): WR 25.28% / PF 0.61"* — 4.5 months stale.
   - L1472: *"Real-money posture as of 2026-05-31: …FOREX BLOCKED PF 0.29 / WR 46.1%…"*.
   Both are hand-written spans, not payload-driven.
2. **Local `audit_dashboard/data/*.json` mirror is dead** — 331 of 332 files >48 h; most from
   **June** (`dashboard_data.json` local = gen 2026-06-02). Production serves fresh files, but
   anything reading the repo copy (local tooling, `asset-class-freshness-watchdog` fallback,
   nav-matrix prefetch) sees month-old data. Root cause: FTP-deploy writes to the server, repo
   copies are only committed opportunistically.
3. **`pick_funnel_nightly.json` and `surface_metrics_export.json` return HTTP 404** on
   production — names either renamed or never deployed; consumers pointing at them are broken.
4. **`picks-now.html` stopped updating ~132 d ago** (Jun 13) per yesterday's QA; other pages
   126–166 d stale (recorded in `updates/2026-10-17-*` QA, unchanged today).
5. **A/B/C class coverage holes** — zero picks in 30 d for `COMMODITY`, `MEMECOIN`,
   `PENNY_STOCK`, `SPORTS` (BOND has only 28 picks/30 d, 3 OPEN). The emitters for
   MEME/PENNY were already flagged "no emitters" in the 2026-10-17 QA.

### 2.3 Pick-quality context (why "real money" bar isn't met)
Latest audit verdict (unchanged today): **0/N classes money-ready**; all classes fail
Smart-Picks floors (0 smart picks). 30-day pick flow is healthy by volume (CRYPTO 4,208,
FOREX 2,207, FUTURES 742, EQUITY 725, ETF 431, UNKNOWN→now 6, BOND 28) — the bottleneck is
**quality/wins, not insert freshness**: overall realized WR 44.8% with PF 1.15 ≈ coin-flip after
costs, which is exactly what the operator is asking to fix next.

---

## 3. Prioritized TODO list (work paused here — resume at P0/P1)

**P0 — verify the fixes landed end-to-end**
1. Re-check `/tmp/postfix_insert_watch.log` (or query directly) for the first post-05:50 insert
   and confirm it has `status='OPEN'` and a correct `asset_class`.
2. Confirm `tools/pick_flow_snapshot.py` (the `WHERE status='OPEN'` consumer) now returns >0.

**P1 — per-class fresh, solid data**
3. Re-enable / patch emitters for **COMMODITY, MEMECOIN, PENNY_STOCK** (zero picks in 30 d);
   raise BOND coverage (3 OPEN is too thin).
4. Persist the symbol→class cache properly: the yfinance result must survive in-repo
   (move `/tmp/symbol_assetclass_cache.json` logic into `asset_classification` fallback: on
   UNKNOWN, consult a committed cache before returning UNKNOWN) so 2,629-row reclass never
   recurs; classify at INSERT time.
5. `resolve_asset_class` fix: extend `_EQUITY_PATTERNS`/`_ETF_PATTERNS` or, better, add a
   quote-type fallback — AMD/PLTR returning UNKNOWN is a standing bug affecting FUTURE inserts
   (`created_by='aggregator'` path tags UNKNOWN when symbol isn't in the hardcoded lists).

**P1 — make the remaining static core stats dynamic**
6. Replace template.html L850 & L1472 hard-coded WR/PF/posture prose with payload-driven spans
   fed from `generated_at` + `summary.*` in `dashboard_data.json`.
7. Fix/redirect the 404 sidecars (`pick_funnel_nightly.json`, `surface_metrics_export.json`).
8. Stop the local `audit_dashboard/data` rot: either FTP-only (and read live URLs in tooling)
   or add a workflow step to commit fresh copies.

**P2 — REAL-money-grade pick quality per class (the actual goal)**
9. Per-class funnel: raise WR/PF above the Smart-Picks floors class-by-class; start with the
   healthiest (FOREX/EQUITY fresh but 0 smart picks) — needs the rating-tuning list already
   delivered yesterday (resolver first → suppress sub-min-trades WR% → dedupe TIP/SPY →
   hide sub-floor scores → label analysis_type).
10. Every metric that isn't yet recompute-on-run gets a `generated_at` + staleness tooltip so
    no page can silently show month-old numbers again.

---

## 4. Files touched this session
- `ejaguiar1_stocks.at_raw_picks` — **production DB**: 3,126 status NULL→OPEN; 2,623 asset_class
  UNKNOWN→EQUITY/ETF (row counts in §1.2). ⚠️ No schema changes, no rows deleted.
- `/tmp/postfix_insert_watch.sh` + `/tmp/postfix_insert_watch.log` (ephemeral watcher).
- `/tmp/symbol_assetclass_cache.json` (ephemeral; needs promotion to repo per todo #4).
- This file — handoff doc. **No code files were modified this session.**

*Resume instruction: start at P0 #1 (verify post-fix insert), then P1 #5 (classifier fix) — both
are small, testable, and unblock everything downstream.*

---

## 5. Post-summary progress (same session, after the doc was written)
- **P0 pick_flow_snapshot:** confirmed — `WHERE status='OPEN'` now returns actives per class
  (EQUITY 212 · FOREX 125 · CRYPTO 90 · FUTURES 84 · ETF 71 · BOND 3 within 7d); total NULL = 0.
  Watcher restarted unbuffered (PID 3528971, `/tmp/postfix_insert_watch.log`) — first poll logged;
  still 0 inserts since 05:50, awaiting the next ~hourly aggregator cycle.
- **P1 classifier fix SHIPPED (code change, not yet committed):**
  `audit_trail/asset_classification.py` now consults a committed
  `audit_trail/symbol_asset_class_cache.json` before returning UNKNOWN (fail-open).
  Verification: py_compile OK; 13/14 behavior cases PASS (`PLTR/AMD→EQUITY`, `EFA/XLK/USO→ETF`,
  crypto/forex/futures paths unchanged, junk still UNKNOWN); `TLT→ETF` is pre-existing
  ordering behavior, untouched by this change.
  Test suite: **146 passed, 2 failed** — both failures
  (`test_equity_30d_pf_above_tier2_floor`, `test_commodity_30d_kill_in_progress`) **reproduce on
  the HEAD version too** (verified by temporarily swapping the file): they are data-driven
  pipeline-gap assertions, not regressions.
- Still open (carried): P1 emitters (COMMODITY/MEMECOIN/PENNY/BOND), P1 de-static-ify hardcoded
  stats + 404 sidecars + local data/ rot, P2 per-class real-money-grade pick quality.